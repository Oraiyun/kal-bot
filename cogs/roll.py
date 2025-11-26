import os
import re
import secrets
from datetime import datetime

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
    async def on_message(self, message):
        if message.author.bot:
            return

        content = message.content.strip().lower()
        match = re.match(r"!r(\d)$", content) or re.match(r"!roll(\d)$", content)

        if match:
            x = int(match.group(1))
            ctx = await self.bot.get_context(message)
            await ctx.invoke(self.roll, x=x)
            return

    # ---------------------------
    #   COMMANDE ROLL — OPTION C + succès physiques
    # ---------------------------
    @commands.command(aliases=["r"])
    async def roll(self, ctx, x: int = 0):
        """OSIRE roll (Option C + succès physiques)."""

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        if x < 0 or x > 3:
            return await ctx.send(
                "Le nombre de dés Bonus doit être compris entre **0** et **3**."
            )

        # Tirages
        base = [secrets.randbelow(6) + 1 for _ in range(3)]
        bonus = [secrets.randbelow(6) + 1 for _ in range(x)]

        title = f"🎲 Jet de 3D6 Auto{' + ' + str(x) + 'D6 Bonus' if x > 0 else ''}"

        # ---------------------------
        # SUCCÈS PHYSIQUES
        # ---------------------------
        count_sixes = base.count(6)
        crit_success = count_sixes == 3  # 3×6 physiques
        auto_success = count_sixes >= 2 and not crit_success  # 2×6 physiques

        # ---------------------------
        # PERFORMANCE (best2 global)
        # ---------------------------
        pool = base + bonus
        performance = sum(sorted(pool)[-2:])

        # ---------------------------
        # STRAIN (pires 2 dés physiques)
        # ---------------------------
        strain = sum(sorted(base)[:2])

        # ---------------------------
        # TOTAL OPTION C
        # ---------------------------
        total_raw = (2 * performance + strain) / 3
        total = round(total_raw)

        # ---------------------------
        # DÉSYNC
        # ---------------------------
        desync_txt = ""
        surcharge_txt = ""
        bonus_sum = 0
        threshold = 0

        if x > 0:
            thresholds = {1: 2, 2: 5, 3: 10}
            threshold = thresholds[x]
            bonus_sum = sum(bonus)

            if bonus_sum < threshold:
                desync_txt = f"Désynchronisation: bonus_sum={bonus_sum} < {threshold}"

        # Surcharge
        if x == 3 and bonus == [6, 6, 6]:
            surcharge_txt = "Surcharge: Triple 6"

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
        if desync_txt and not crit_success:
            embed.add_field(
                name="⚠ Désynchronisation",
                value=f"Somme des bonus = {bonus_sum} < seuil {threshold}",
                inline=False,
            )

        # Surcharge (sauf si critique)
        if surcharge_txt and not crit_success:
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
