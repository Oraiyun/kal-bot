import os
import re
import secrets
import string
from datetime import datetime
from itertools import count

import discord
from discord.ext import commands


class Roll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------
    #   Logger des jets
    # ---------------------------
    def log_roll(
        self,
        user,
        x,
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
        log_folder = "logs"
        os.makedirs(log_folder, exist_ok=True)

        log_path = os.path.join(log_folder, "rolls.txt")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        base_str = ", ".join(str(d) for d in base)
        bonus_str = ", ".join(str(d) for d in bonus)

        line = (
            f"[{timestamp}] {user} | x={x} | base=[{base_str}] | bonus=[{bonus_str}] "
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

    # ---------------------------
    #   MATCH !rX / !rollX
    # ---------------------------
    @commands.Cog.listener()
    async def on_message(
        self,
        message,
    ):
        if message.author.bot:
            return

        content = message.content.strip().lower()
        match = re.match(r"!(?:r|roll)(\d)$", content)

        if match:
            x = int(match.group(1))
            ctx = await self.bot.get_context(message)
            await ctx.invoke(self.roll, x=x)
            return

    # ---------------------------
    #   COMMANDE ROLL — OPTION C + succès physiques
    # ---------------------------
    @commands.command(aliases=["r"])
    async def roll(self, ctx, x: int = 0, variable_name: str = ""):
        """OSIRE roll (Option C + succès physiques)."""

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        if x < 0 or x > 3:
            return await ctx.send(
                "Le nombre de dés Bonus doit être compris entre **0** et **3**."
            )
        print("----------------- RESET -------------------")
        # Tirages
        base = [secrets.randbelow(6) + 1 for _ in range(3)]
        bonus = [secrets.randbelow(6) + 1 for _ in range(x)]
        de_variable = secrets.randbelow(6) + 1

        title = f"🎲 Jet de 3D6 Auto{' + ' + str(x) + 'D6 Bonus' if x > 0 else ''}"

        # Dé variable
        if variable_name.lower() == "s":
            variable_name = "surcharge"
        elif variable_name.lower() == "o":
            variable_name = "overload"

        # ---------------------------
        # SUCCÈS PHYSIQUES
        # ---------------------------
        count_sixes = base.count(6)
        crit_success = True if count_sixes == 3 else False
        auto_success = True if count_sixes == 2 else False

        # ---------------------------
        # PERFORMANCE (best2 global)
        # ---------------------------
        pool = base + bonus
        performance = sum(sorted(pool)[-2:])

        # ---------------------------
        # STRAIN (pires 2 dés physiques)
        # ---------------------------
        strain = sum(sorted(base)[:2])

        # Surcharge
        surcharge = False
        surcharge_sixes = 0
        print(f"Six de base = {count_sixes}")
        print(f"Six bonus = {bonus.count(6)}")
        print(f"Dé variable = {de_variable}")
        if count_sixes <= 1:
            surcharge_sixes = count_sixes + bonus.count(6)
            if variable_name == "surcharge" and de_variable >= 4:
                de_variable = 6
                print(f"Dé variable post = {de_variable}")
                surcharge_sixes += 1
            if surcharge_sixes >= 3:
                surcharge = True
        print(f"Qte de 6 de surcharge : {surcharge_sixes}")

        # ---------------------------
        # TOTAL OPTION C
        # ---------------------------
        total_raw = (2 * performance + strain) / 3
        total = round(total_raw)

        # ---------------------------
        # DÉSYNC
        # ---------------------------
        desync = False
        bonus_sum = 0
        threshold = 0
        desync_txt = ""
        surcharge_txt = ""

        if x > 0:
            thresholds = {1: 2, 2: 5, 3: 10}
            threshold = thresholds[x]
            bonus_sum = sum(bonus)

            if bonus_sum < threshold:
                desync_txt = f"Désynchronisation: bonus_sum={bonus_sum} < {threshold}"
                desync = True

        # ---------------------------
        # EMBED
        # ---------------------------
        embed = discord.Embed(
            title=title,
            color=discord.Color.from_rgb(0, 180, 255),
        )

        embed.add_field(name="Lanceur", value=ctx.author.mention, inline=False)

        embed.add_field(
            name="Dés Physiques", value=", ".join(str(d) for d in base), inline=False
        )

        if x > 0:
            embed.add_field(
                name="Dés Bonus", value=", ".join(str(d) for d in bonus), inline=False
            )

        if variable_name == "surcharge":
            embed.add_field(
                name="Dé de Surcharge",
                value=de_variable,
                inline=False,
            )

        embed.add_field(
            name="Performance (2 meilleurs dés globaux)",
            value=str(performance),
            inline=False,
        )
        embed.add_field(
            name="Strain (2 pires physiques)",
            value=str(strain),
            inline=False,
        )
        embed.add_field(name="Résultat", value=str(total), inline=False)

        # ---- AJOUTS : SUCCÈS PHYSIQUES ----
        if crit_success:
            embed.add_field(
                name="Succès Critique (Physique)",
                value="Les 3 dés physiques sont des 6.",
                inline=False,
            )
        elif auto_success:
            embed.add_field(
                name="Succès Automatique (Physique)",
                value="Au moins 2 dés physiques sont des 6.",
                inline=False,
            )

        # Désynchronisation (sauf si succès critique)
        if desync and not (crit_success or auto_success):
            embed.add_field(
                name="⚠ Désynchronisation",
                value=f"Somme des bonus = {bonus_sum} < seuil {threshold}",
                inline=False,
            )

        # Surcharge (sauf si critique)
        if surcharge and not (crit_success or auto_success):
            embed.add_field(name="Surcharge", value="**Triple 6**", inline=False)

        # ---------------------------
        # LOGGING
        # ---------------------------
        self.log_roll(
            user=str(ctx.author),
            x=x,
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

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Roll(bot))
