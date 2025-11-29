import os
import secrets
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class Roll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================================================
    #  FONCTION CENTRALE : log + calculs + embed
    # ============================================================
    async def generate_roll(self, user, bonus_dice: int, mode: str):
        # ---------------------------
        # Tirages
        # ---------------------------
        base = [secrets.randbelow(6) + 1 for _ in range(3)]
        bonus = [secrets.randbelow(6) + 1 for _ in range(bonus_dice)]
        variable_die = secrets.randbelow(6) + 1

        # Normalisation du mode
        mode = mode.lower()
        if mode == "s":
            mode = "surcharge"
        elif mode == "o":
            mode = "overload"

        # ---------------------------
        # SUCCÈS PHYSIQUES
        # ---------------------------
        count_sixes = base.count(6)
        crit_success = count_sixes == 3
        auto_success = count_sixes == 2

        # ---------------------------
        # PERFORMANCE
        # ---------------------------
        pool = base + bonus
        if mode == "overload":
            pool.append(variable_die)
        performance = sum(sorted(pool)[-2:])

        # ---------------------------
        # STRAIN
        # ---------------------------
        strain = sum(sorted(base)[:2])

        # ---------------------------
        # SURCHARGE
        # ---------------------------
        surcharge = False
        surcharge_count = 0
        surcharge_txt = ""

        if count_sixes <= 1:
            surcharge_count = count_sixes + bonus.count(6)

            if mode == "surcharge" and variable_die >= 4:
                variable_die = 6
                surcharge_count += 1

            if surcharge_count >= 3:
                surcharge = True
                surcharge_txt = f"Surcharge détectée ({surcharge_count} six)"

        # ---------------------------
        # TOTAL
        # ---------------------------
        total = round((2 * performance + strain) / 3)

        # ---------------------------
        # DÉSYNC
        # ---------------------------
        desync = False
        desync_txt = ""
        if bonus_dice > 0:
            thresholds = {1: 2, 2: 5, 3: 10}
            threshold = thresholds[bonus_dice]
            bonus_sum = sum(bonus)

            if bonus_sum < threshold:
                desync = True
                desync_txt = f"Désynchronisation: bonus_sum={bonus_sum} < {threshold}"

        # ---------------------------
        # EMBED
        # ---------------------------
        title = f"🎲 Jet de 3D6 Auto{' + ' + str(bonus_dice) + 'D6 Bonus' if bonus_dice > 0 else ''}"
        embed = discord.Embed(title=title, color=discord.Color.from_rgb(0, 180, 255))

        embed.add_field(name="Lanceur", value=user.mention, inline=False)

        inline_exception = True if bonus else False

        embed.add_field(
            name="Dés Physiques",
            value=", ".join(str(d) for d in base),
            inline=inline_exception,
        )

        if bonus_dice > 0:
            embed.add_field(
                name="Dés Bonus", value=", ".join(str(d) for d in bonus), inline=True
            )

        if mode == "surcharge":
            embed.add_field(
                name=f"Dé de Surcharge : {variable_die}", value="", inline=False
            )
        if mode == "overload":
            embed.add_field(
                name=f"Dé d'Overload : {variable_die}", value="", inline=False
            )

        embed.add_field(name="Performance", value=str(performance), inline=False)
        embed.add_field(name="Strain", value=str(strain), inline=True)
        embed.add_field(name="Résultat", value=str(total), inline=False)

        if crit_success:
            embed.add_field(
                name="Succès Critique",
                value="Les 3 dés physiques sont des 6.",
                inline=False,
            )
        elif auto_success:
            embed.add_field(
                name="Succès Automatique",
                value="Au moins 2 dés physiques sont des 6.",
                inline=False,
            )

        if desync and not (crit_success or auto_success):
            embed.add_field(name="⚠ Désynchronisation", value=desync_txt, inline=False)

        if surcharge and not (crit_success or auto_success):
            embed.add_field(name="Surcharge", value="**Triple 6**", inline=False)

        if not crit_success and not auto_success:
            embed.set_footer(text="Seuil (Résultat + Compétence) : 13")

        # ---------------------------
        # LOG
        # ---------------------------
        self.log_roll(
            user=str(user),
            bonus_dice=bonus_dice,
            base=base,
            bonus=bonus,
            performance=performance,
            strain=strain,
            total=total,
            auto_success=auto_success,
            crit_success=crit_success,
            desync_msg=desync_txt,
            surcharge_msg=surcharge_txt,
        )

        return embed

    # ---------------------------
    #   Logger
    # ---------------------------
    def log_roll(
        self,
        user,
        bonus_dice,
        base,
        bonus,
        performance,
        strain,
        total,
        auto_success,
        crit_success,
        desync_msg="",
        surcharge_msg="",
    ):
        os.makedirs("logs", exist_ok=True)
        log_path = "logs/rolls.txt"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base_str = ", ".join(str(d) for d in base)
        bonus_str = ", ".join(str(d) for d in bonus)

        line = (
            f"[{timestamp}] {user} | bonus_dice={bonus_dice} "
            f"| base=[{base_str}] | bonus=[{bonus_str}] "
            f"| performance={performance} | strain={strain} | total={total}"
        )
        if auto_success:
            line += " | Succès automatique"
        if crit_success:
            line += " | Succès critique"
        if desync_msg:
            line += f" | {desync_msg}"
        if surcharge_msg:
            line += f" | {surcharge_msg}"
        line += "\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)

    # ============================================================
    #  AUTOCOMPLETE
    # ============================================================
    async def mode_autocomplete(self, interaction, current: str):
        options = ["surcharge", "overload", "s", "o"]
        return [
            app_commands.Choice(name=o, value=o)
            for o in options
            if current.lower() in o.lower()
        ]

    # ============================================================
    #  SLASH COMMAND : /roll
    # ============================================================
    @app_commands.command(name="roll", description="Moteur de jet OSIRE")
    @app_commands.describe(
        bonus_dice="Nombre de dés bonus (0 à 3)", mode="surcharge (s) ou overload (o)"
    )
    @app_commands.autocomplete(mode=mode_autocomplete)
    async def roll_slash(
        self, interaction: discord.Interaction, bonus_dice: int = 0, mode: str = ""
    ):
        if bonus_dice < 0 or bonus_dice > 3:
            await interaction.response.send_message(
                "Le nombre de dés bonus doit être compris entre **0** et **3**.",
                ephemeral=True,
            )
            return

        embed = await self.generate_roll(interaction.user, bonus_dice, mode)
        await interaction.response.send_message(embed=embed)

    # ============================================================
    #  PREFIX COMMAND : !roll
    # ============================================================
    @commands.command(name="roll", aliases=["r"])
    async def roll_prefix(self, ctx: commands.Context, *args):
        bonus_dice = 0
        mode = ""

        # Analyse automatique des arguments
        for arg in args:
            arg_lower = arg.lower()

            # Si c'est un nombre → bonus_dice
            if arg.isdigit():
                bonus_dice = int(arg)
                continue

            # Si c'est un mode
            if arg_lower in ["s", "surcharge", "o", "overload"]:
                mode = arg_lower
                continue

        embed = await self.generate_roll(ctx.author, bonus_dice, mode)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Roll(bot))
