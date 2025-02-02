import discord
from discord.ext import commands
import json
import asyncio
from datetime import datetime

# Charger la configuration
with open('config.json') as config_file:
    config = json.load(config_file)

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.invites = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix=config["prefix"], intents=intents)
invite_cache = {}

# Fonction pour récupérer les invitations d'un serveur
async def fetch_invites(guild):
    invites = await guild.invites()
    return {invite.code: invite for invite in invites}

# Event : Bot prêt
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    for guild in bot.guilds:
        invite_cache[guild.id] = await fetch_invites(guild)

# Event : Nouveau membre rejoint
@bot.event
async def on_member_join(member):
    await asyncio.sleep(1)
    guild = member.guild
    new_invites = await fetch_invites(guild)
    old_invites = invite_cache.get(guild.id, {})

    inviter = None
    for code, invite in new_invites.items():
        if code in old_invites and invite.uses > old_invites[code].uses:
            inviter = invite.inviter
            break

    invite_cache[guild.id] = new_invites
    log_channel = bot.get_channel(int(config["log_channel_id"]))

    embed = discord.Embed(title="📥 Nouveau membre", color=0x57F287)
    if inviter:
        embed.description = f"**{member.mention}** a été invité par **{inviter.mention}**.\nInvitations utilisées : {invite.uses}"
    else:
        embed.description = f"**{member.mention}** a rejoint, mais l'invitation est inconnue."

    await log_channel.send(embed=embed)

# Event : Membre quitte
@bot.event
async def on_member_remove(member):
    log_channel = bot.get_channel(int(config["log_channel_id"]))
    embed = discord.Embed(title="📤 Membre parti", description=f"**{member.name}** a quitté le serveur.", color=0xED4245)
    await log_channel.send(embed=embed)

# === Commandes du bot ===

# 1. Statistiques d'invitations
@bot.command(name='invites')
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    invites = await ctx.guild.invites()
    total_invites = sum(invite.uses for invite in invites if invite.inviter == member)

    embed = discord.Embed(
        title="📊 Statistiques d'invitations",
        description=f"**{member.mention}** a invité **{total_invites}** membres !",
        color=0x3498DB
    )
    await ctx.send(embed=embed)

# 2. Liste des invitations actives
@bot.command(name='invitelist')
async def invitelist(ctx):
    invites = await ctx.guild.invites()
    embed = discord.Embed(title="🔗 Invitations actives", color=0x00FFFF)
    for invite in invites:
        embed.add_field(
            name=f"Code : {invite.code}",
            value=f"Invité par : {invite.inviter.mention}\nUtilisations : {invite.uses}",
            inline=False
        )
    await ctx.send(embed=embed)

# 3. Classement des meilleurs inviteurs
@bot.command(name='topinvites')
async def topinvites(ctx):
    invites = await ctx.guild.invites()
    inviter_count = {}

    for invite in invites:
        inviter = invite.inviter
        inviter_count[inviter] = inviter_count.get(inviter, 0) + invite.uses

    top_invites = sorted(inviter_count.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(title="🏆 Top 10 des inviteurs", color=0xFFD700)
    for i, (inviter, count) in enumerate(top_invites, start=1):
        embed.add_field(name=f"{i}. {inviter}", value=f"{count} invitations", inline=False)

    await ctx.send(embed=embed)

# 4. Créer une invitation personnalisée
@bot.command(name='createinvite')
async def createinvite(ctx, max_uses: int = 1, max_age: int = 3600):
    invite = await ctx.channel.create_invite(max_uses=max_uses, max_age=max_age)
    await ctx.send(f"🔗 Nouvelle invitation : {invite.url}")

# 5. Supprimer une invitation par code
@bot.command(name='deleteinvite')
async def deleteinvite(ctx, code: str):
    try:
        invite = await ctx.guild.fetch_invite(code)
        await invite.delete()
        await ctx.send(f"✅ Invitation `{code}` supprimée avec succès.")
    except:
        await ctx.send("❌ Invitation introuvable.")

# 6. Compter le nombre total d'invitations
@bot.command(name='totalinvites')
async def totalinvites(ctx):
    invites = await ctx.guild.invites()
    total = sum(invite.uses for invite in invites)
    await ctx.send(f"📊 Nombre total d'invitations utilisées : **{total}**")

# 7. Vérifier l'inviteur d'un utilisateur
@bot.command(name='whoinvited')
async def whoinvited(ctx, member: discord.Member):
    invites = await ctx.guild.invites()
    inviter = None
    for invite in invites:
        if invite.uses > 0 and invite.inviter == member:
            inviter = invite.inviter
            break
    if inviter:
        await ctx.send(f"**{member.mention}** a été invité par **{inviter.mention}**.")
    else:
        await ctx.send(f"Impossible de déterminer qui a invité **{member.mention}**.")

# 8. Invitations d'un utilisateur spécifique
@bot.command(name='invitedby')
async def invitedby(ctx, member: discord.Member):
    invites = await ctx.guild.invites()
    total = sum(invite.uses for invite in invites if invite.inviter == member)
    await ctx.send(f"**{member.mention}** a invité **{total}** personnes.")

# 9. Lister les invitations par salon
@bot.command(name='invitesbychannel')
async def invitesbychannel(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    invites = await channel.invites()
    embed = discord.Embed(title=f"🔗 Invitations dans #{channel.name}", color=0x00FFFF)
    for invite in invites:
        embed.add_field(
            name=f"Code : {invite.code}",
            value=f"Invité par : {invite.inviter.mention} - Utilisations : {invite.uses}",
            inline=False
        )
    await ctx.send(embed=embed)

# 10. Invitation avec le plus d'utilisations
@bot.command(name='mostusedinvite')
async def mostusedinvite(ctx):
    invites = await ctx.guild.invites()
    most_used = max(invites, key=lambda x: x.uses, default=None)
    if most_used:
        await ctx.send(f"🏅 L'invitation la plus utilisée est `{most_used.code}` par {most_used.inviter} avec {most_used.uses} utilisations.")
    else:
        await ctx.send("Aucune invitation trouvée.")

# Commande d'aide personnalisée
@bot.command(name='aide')
async def help_command(ctx):
    embed = discord.Embed(title="📚 Commandes du Invite Logger", color=0x5865F2)
    embed.add_field(name="`?invites [@membre]`", value="Affiche le nombre d'invitations d'un membre.", inline=False)
    embed.add_field(name="`?invitelist`", value="Affiche la liste des invitations actives.", inline=False)
    embed.add_field(name="`?topinvites`", value="Classement des meilleurs inviteurs.", inline=False)
    embed.add_field(name="`?createinvite`", value="Crée une nouvelle invitation.", inline=False)
    embed.add_field(name="`?deleteinvite <code>`", value="Supprime une invitation par son code.", inline=False)
    embed.add_field(name="`?totalinvites`", value="Nombre total d'invitations utilisées.", inline=False)
    embed.add_field(name="`?whoinvited @membre`", value="Affiche qui a invité un utilisateur.", inline=False)
    embed.add_field(name="`?invitedby @membre`", value="Combien de personnes un membre a invité.", inline=False)
    embed.add_field(name="`?invitesbychannel`", value="Affiche les invitations par salon.", inline=False)
    embed.add_field(name="`?mostusedinvite`", value="Invitation la plus utilisée.", inline=False)
    await ctx.send(embed=embed)

# Lancer le bot
bot.run(config["token"])
