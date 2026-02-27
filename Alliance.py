import discord
from discord.ext import commands
import os
from keep_alive import keep_alive
from discord.ext import commands
from discord import app_commands, Embed, Colour
from dotenv import load_dotenv
from datetime import datetime
import io
import requests
from flask import Flask, request


app = Flask(__name__)
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_FINANCE_WEBHOOK = os.getenv("DISCORD_FINANCE_WEBHOOK")
OWNER_ID = 445238427865055232

BOOST_ANNOUNCE_CHANNELS = {
    1465849358741278854: 1465854737839820982,
}

ADMIN_ROLES = {
    1465849358741278854: [1467218940005585149, 1467219333380837681, 1472024901258055812, 1472024513389531352, 1467220155523404005, 1467227442883334215, 1467228317357838467, 1467228889469292796],
}

LOG_CHANNELS = {
    1465849358741278854: 1471880187124912271,
}

DISCORD_LINK_CHANNELS = {
    1271212491568975944: [1318165877350338612, 1313203999004164230],
}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

LOGS_DISCORD = 1471880187124912271


async def set_bot_status():
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="🏳 | Alliance RP")
    )

def user_is_admin(interaction):
    guild_id = interaction.guild.id
    allowed_role_ids = ADMIN_ROLES.get(guild_id, [])
    return any(role.id in allowed_role_ids for role in interaction.user.roles)


@bot.event
async def on_ready():
    await set_bot_status()
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")

@app.post("/paypal-webhook")
def paypal_webhook():
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type", "UNKNOWN")

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        resource = data.get("resource", {})
        
        amount = resource.get("amount", {}).get("value", "?")
        currency = resource.get("amount", {}).get("currency_code", "EUR")
        transaction_id = resource.get("id", "N/A")
        
        payer = resource.get("payer", {})
        name_data = payer.get("name", {})
        first_name = name_data.get("given_name", "Donateur")

        content = (
            f"💸 **Paiement reçu**\n"
            f"👤 Donateur : {first_name}\n"
            f"💰 Montant : {amount} {currency}\n"
            f"🧾 Transaction : `{transaction_id}`"
        )

        if DISCORD_FINANCE_WEBHOOK:
            requests.post(DISCORD_FINANCE_WEBHOOK, json={"content": content})

    return "OK", 200


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if '@everyone' in message.content or '@here' in message.content:
        guild_id = message.guild.id
        allowed_role_ids = ADMIN_ROLES.get(guild_id, [])

        if not any(role.id in allowed_role_ids for role in message.author.roles):
            try:
                await message.delete()
            except discord.NotFound:
                pass
            await message.channel.send(
                "Ton message contenant 'everyone' ou 'here' a été supprimé car tu n'as pas les permissions.",
                delete_after=30
            )

            log_channel_id = LOG_CHANNELS.get(guild_id)
            log_channel = message.guild.get_channel(log_channel_id) if log_channel_id else None
            if log_channel:
                embed = Embed(
                    title="🔒 Message supprimé",
                    description=f"**Auteur :** {message.author.mention}\n"
                                f"**Contenu :**\n```{message.content}```",
                    color=0xFF0000
                )
                embed.set_footer(text=f"Salon : #{message.channel.name} • ID : {message.channel.id}")
                embed.timestamp = message.created_at
                await log_channel.send(embed=embed)

    guild_id = message.guild.id
    allowed_role_ids = ADMIN_ROLES.get(guild_id, [])
    log_channel_id = LOG_CHANNELS.get(guild_id)
    log_channel = message.guild.get_channel(log_channel_id) if log_channel_id else None
    channels_to_check = DISCORD_LINK_CHANNELS.get(guild_id, [])

    if message.channel.id in channels_to_check and "discord.gg" in message.content.lower():
    # ✅ Vérifie si l'utilisateur a au moins un rôle autorisé (staff)
        if not any(role.id in allowed_role_ids for role in getattr(message.author, "roles", [])):
            try:
                await message.delete()
            except discord.NotFound:
                pass

            await message.channel.send(
                "⛔ Lien Discord non autorisé. Ton message a été supprimé.",
                delete_after=10
            )

            if log_channel:
                embed = discord.Embed(
                    title="🔗 Lien Discord supprimé",
                    description="Un lien Discord a été posté par un survivant.",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Auteur", value=message.author.mention, inline=True)
                embed.add_field(name="Salon", value=message.channel.mention, inline=True)
                embed.add_field(name="Contenu", value=f"```{message.content}```", inline=False)
                embed.timestamp = message.created_at
                await log_channel.send(embed=embed)
    

    await bot.process_commands(message)

@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)

    if not message.guild:
        return

    # Détecte uniquement un boost
    if message.type != discord.MessageType.premium_guild_subscription:
        return

    guild = message.guild
    booster = message.author

    channel_id = BOOST_ANNOUNCE_CHANNELS.get(guild.id)
    channel = guild.get_channel(channel_id) if channel_id else message.channel
    if not channel:
        return

    embed = discord.Embed(
        title="🚀 Nouveau boost serveur !",
        description=f"{booster.mention} vient de booster le serveur ! Merci beaucoup pour ton soutien ❤️",
        color=0x9b59ff
    )

    embed.set_footer(text="Alliance RP • Merci pour votre soutien 💜")

    await channel.send(embed=embed)



# ===============================
# ====== COMMANDES MODO =========
# ===============================

@bot.tree.command(name="purge", description="Supprime un nombre spécifié de messages.")
async def purge(interaction: discord.Interaction, number: int):
    if not user_is_admin(interaction):
        await interaction.response.send_message("Vous n'avez pas les permissions nécessaires pour utiliser cette commande.", ephemeral=True)
        return

    if number <= 0:
        await interaction.response.send_message("Veuillez spécifier un nombre positif de messages à supprimer.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=number)
    await interaction.followup.send(f"{len(deleted)} messages ont été supprimés.", ephemeral=True)
    

@bot.tree.command(name="topserveur", description="Message de vote accessible uniquement au staff")
async def topserveur(interaction: discord.Interaction):
    if not user_is_admin(interaction):
        await interaction.response.send_message("❌ Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    await interaction.response.send_message(
        "---"  # Mention du rôle staff en dur ici
    )

@bot.tree.command(name="serverinfo", description="Affiche les informations du serveur.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    roles = sorted([role for role in guild.roles if role.name != "@everyone"], key=lambda r: r.position, reverse=True)
    roles_list = "\n".join([role.name for role in roles])
    owner = guild.owner
    server_info = (
        f"Serveur: {guild.name}\n"
        f"Membres: {guild.member_count}\n"
        f"Créé le: {guild.created_at.strftime('%d/%m/%Y')}\n"
        f"Propriétaire: {owner.mention}\n\n"
        f"Rôles:\n{roles_list}"
    )
    await interaction.response.send_message(server_info, ephemeral=True)

@bot.tree.command(name="message", description="Faites une annonce dans le serveur.")
async def annonce(interaction: discord.Interaction, message: str):
    if not user_is_admin(interaction):
        await interaction.response.send_message("Désolé, vous n'avez pas les permissions pour faire une annonce.", ephemeral=True)
        return

    formatted_message = f"**{message}**"
    await interaction.channel.send(formatted_message)
    await interaction.response.send_message("Annonce envoyée avec succès!", ephemeral=True)

@bot.tree.command(name="annonce", description="Faites une annonce stylée dans le serveur.")
async def annonce(interaction: discord.Interaction, message: str):
    if not user_is_admin(interaction):
        await interaction.response.send_message(
            "Désolé, vous n'avez pas les permissions pour faire une annonce.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="📢 Annonce Officielle",
        description=message,
        color=discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )

    # Signature Alliance RP
    embed.set_footer(text="Alliance RP")
    embed.set_author(
        name="Alliance RP",
        icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else discord.Embed.Empty
    )

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Annonce envoyée avec succès!", ephemeral=True)


@bot.tree.command(name="userinfo", description="Infos d'un membre.")
@app_commands.describe(membre="Le membre (optionnel)")
async def userinfo_cmd(interaction: discord.Interaction, membre: discord.Member = None):
    membre = membre or interaction.user

    roles = [r.mention for r in membre.roles if r != interaction.guild.default_role]
    roles_text = " ".join(roles[:20]) if roles else "Aucun"

    embed = discord.Embed(
        title="👤 User Info",
        description=membre.mention,
        color=0x9b59ff
    )
    embed.add_field(name="ID", value=str(membre.id), inline=True)
    embed.add_field(name="Pseudo", value=membre.display_name, inline=True)
    embed.add_field(name="Compte créé", value=discord.utils.format_dt(membre.created_at, style="F"), inline=False)

    if membre.joined_at:
        embed.add_field(name="A rejoint", value=discord.utils.format_dt(membre.joined_at, style="F"), inline=False)

    embed.add_field(name="Rôles", value=roles_text, inline=False)
    embed.set_footer(text="Alliance RP • Infos")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="maintenance", description="Annonce une maintenance.")
@app_commands.describe(message="Détails de la maintenance")
async def maintenance_cmd(interaction: discord.Interaction, message: str):
    if not user_is_admin(interaction):
        return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

    embed = discord.Embed(
        title="🛠️ Maintenance",
        description=message,
        color=0x9b59ff
    )
    embed.set_footer(text="Alliance RP • Information")

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Maintenance envoyée.", ephemeral=True)


@bot.tree.command(name="event", description="Annonce un event.")
@app_commands.describe(titre="Titre de l'event", description="Description de l'event")
async def event_cmd(interaction: discord.Interaction, titre: str, description: str):
    if not user_is_admin(interaction):
        return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

    embed = discord.Embed(
        title=f"🎉 Event • {titre}",
        description=description,
        color=0x9b59ff
    )
    embed.set_footer(text="Alliance RP • Event")

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Event envoyé.", ephemeral=True)


import discord
from discord import app_commands

@bot.tree.command(name="lock", description="Verrouille le salon actuel (empêche @everyone d'écrire).")
@app_commands.describe(raison="Raison (optionnel)")
async def lock_cmd(interaction: discord.Interaction, raison: str = None):
    if not user_is_admin(interaction):
        return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return await interaction.response.send_message("❌ Cette commande fonctionne dans un salon texte.", ephemeral=True)

    # Pour les threads, on peut les verrouiller/archiver
    if isinstance(channel, discord.Thread):
        try:
            await channel.edit(locked=True, reason=raison or f"Lock par {interaction.user}")
            embed = discord.Embed(
                title="🔒 Thread verrouillé",
                description=f"{channel.mention} est maintenant verrouillé.",
                color=0x9b59ff
            )
            if raison:
                embed.add_field(name="Raison", value=raison, inline=False)
            embed.set_footer(text="Alliance RP • Modération")
            return await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Je n'ai pas la permission de verrouiller ce thread.", ephemeral=True)

    # Salon texte normal : on bloque @everyone
    everyone = interaction.guild.default_role
    overwrites = channel.overwrites_for(everyone)

    # Déjà lock ?
    if overwrites.send_messages is False:
        return await interaction.response.send_message("✅ Salon déjà verrouillé.", ephemeral=True)

    overwrites.send_messages = False
    try:
        await channel.set_permissions(everyone, overwrite=overwrites, reason=raison or f"Lock par {interaction.user}")
    except discord.Forbidden:
        return await interaction.response.send_message("❌ Je n'ai pas la permission de modifier les permissions.", ephemeral=True)

    embed = discord.Embed(
        title="🔒 Salon verrouillé",
        description=f"{channel.mention} est maintenant verrouillé ( @everyone ne peut plus écrire ).",
        color=0x9b59ff
    )
    if raison:
        embed.add_field(name="Raison", value=raison, inline=False)
    embed.set_footer(text="Alliance RP • Modération")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="unlock", description="Déverrouille le salon actuel (autorise @everyone à écrire).")
@app_commands.describe(raison="Raison (optionnel)")
async def unlock_cmd(interaction: discord.Interaction, raison: str = None):
    if not user_is_admin(interaction):
        return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return await interaction.response.send_message("❌ Cette commande fonctionne dans un salon texte.", ephemeral=True)

    # Threads
    if isinstance(channel, discord.Thread):
        try:
            await channel.edit(locked=False, reason=raison or f"Unlock par {interaction.user}")
            embed = discord.Embed(
                title="🔓 Thread déverrouillé",
                description=f"{channel.mention} est maintenant déverrouillé.",
                color=0x9b59ff
            )
            if raison:
                embed.add_field(name="Raison", value=raison, inline=False)
            embed.set_footer(text="Alliance RP • Modération")
            return await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Je n'ai pas la permission de déverrouiller ce thread.", ephemeral=True)

    # Salon texte normal : on remet send_messages à None (hérite des permissions)
    everyone = interaction.guild.default_role
    overwrites = channel.overwrites_for(everyone)

    # Déjà unlock (pas explicitement interdit)
    if overwrites.send_messages is not False:
        return await interaction.response.send_message("✅ Salon déjà déverrouillé.", ephemeral=True)

    overwrites.send_messages = None
    try:
        await channel.set_permissions(everyone, overwrite=overwrites, reason=raison or f"Unlock par {interaction.user}")
    except discord.Forbidden:
        return await interaction.response.send_message("❌ Je n'ai pas la permission de modifier les permissions.", ephemeral=True)

    embed = discord.Embed(
        title="🔓 Salon déverrouillé",
        description=f"{channel.mention} est maintenant déverrouillé ( @everyone peut écrire ).",
        color=0x9b59ff
    )
    if raison:
        embed.add_field(name="Raison", value=raison, inline=False)
    embed.set_footer(text="Alliance RP • Modération")

    await interaction.response.send_message(embed=embed)

                

@bot.tree.command(name="testboost", description="Simule un boost (test)")
async def test_boost(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Commande réservée au owner.", ephemeral=True
        )

    guild = interaction.guild

    channel_id = BOOST_ANNOUNCE_CHANNELS.get(guild.id)
    channel = guild.get_channel(channel_id) if channel_id else interaction.channel
    if not channel:
        return await interaction.response.send_message(
            "❌ Salon introuvable.", ephemeral=True
        )

    embed = discord.Embed(
        title="🚀 Nouveau boost serveur !",
        description=f"{interaction.user.mention} vient de booster le serveur ! Merci beaucoup pour ton soutien ❤️",
        color=0x9b59ff
    )

    embed.set_footer(text="Alliance RP • Merci pour votre soutien 💜")

    await channel.send(embed=embed)
    await interaction.response.send_message("✅ Test boost envoyé !", ephemeral=True)


    

keep_alive()

bot.run(TOKEN)

