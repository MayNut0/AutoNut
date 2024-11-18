import discord
from discord import app_commands
from discord.ext import commands
from file_io import load_channel_setting, save_channel_setting
from utils import translate_text_deepl, is_not_korean

# 메인 Embed 생성 함수
def create_autotrans_setting_embed(guild, channel, channel_setting):
    autotrans_setting = channel_setting.get(str(channel.id), {}).get('auto_translate', False)
    return discord.Embed(
        title="자동번역 설정",
        description=(
            f"📢 **안내**\n"
            f"- 현재 채널의 자동번역 상태를 설정할 수 있습니다.\n\n"
            f"📌 **현재 채널**\n"
            f"- {guild.name} > {channel.name}\n\n"
            f"⚒️ **현재 채널 설정**\n"
            f"- 자동번역 : **{'ON' if autotrans_setting else 'OFF'}**"
        ),
        color=discord.Color.blue()
    )

# 돌아가기 버튼 로직
async def handle_back_button(interaction, view_class):
    channel_setting = await load_channel_setting()
    original_embed = create_autotrans_setting_embed(
        interaction.guild, interaction.channel, channel_setting
    )
    await interaction.response.edit_message(embed=original_embed, view=view_class(channel_setting))

# 돌아가기 버튼 View
class ViewBackButton(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(emoji="⬅️", label="돌아가기", style=discord.ButtonStyle.grey)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_back_button(interaction, ViewAutoTransSetting)

# 자동번역 설정창
class ViewAutoTransSetting(discord.ui.View):
    def __init__(self, channel_setting, channel):
        super().__init__()
        self.channel = channel  # 채널 정보 추가
        self.update_button_label(channel_setting)

    def update_button_label(self, channel_setting):
        # 채널 ID가 포함된 설정 확인
        channel_id = str(self.channel.id)
        if channel_setting.get(channel_id, {}).get('auto_translate', False):
            self.children[0].label = "끄기"
            self.children[0].emoji = "⛔"
        else:
            self.children[0].label = "켜기"
            self.children[0].emoji = "✅"

    # 켜기/끄기
    @discord.ui.button(emoji="✅", label="켜기", style=discord.ButtonStyle.green, row=0)
    async def toggle_autotranslate(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_id = str(interaction.channel.id)  # 채널 ID 수정
        channel_setting = await load_channel_setting()
        auto_translate = channel_setting.get(channel_id, {}).get('auto_translate', False)

        # 설정 토글
        channel_setting[channel_id] = {"auto_translate": not auto_translate}
        await save_channel_setting(channel_setting)

        # Embed 업데이트
        new_embed = discord.Embed(
            title=f"🚀 자동번역을 {'종료' if auto_translate else '시작'}합니다!",
            description=f"현재 채널의 자동번역 설정이 **{'ON' if not auto_translate else 'OFF'}** 으로 변경되었습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=new_embed, view=ViewBackButton())

# 메시지 자동번역 기능
class AutoTranslate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_settings = {}  # 채널별 설정 캐싱
        self.bot.loop.create_task(self.load_auto_trans_settings())  # 초기화 시 설정 로드

    async def load_auto_trans_settings(self):
        self.channel_settings = await load_channel_setting()  # 파일에서 데이터 로드

    async def save_auto_trans_settings(self):
        await save_channel_setting(self.channel_settings)  # 변경된 데이터를 파일에 저장

    # 메시지 이벤트 처리: 한글 외 메시지 자동 번역
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return  # 봇 메시지는 무시

        channel_id = str(message.channel.id)
        if self.channel_settings.get(channel_id, {}).get('auto_translate', False):
            # 한국어 메시지 감지
            if is_not_korean(message.content):
                permissions = message.channel.permissions_for(message.guild.me)
                if not permissions.send_messages:
                    return

                # 번역 처리
                translated_text = await translate_text_deepl(message.content)
                response = f"**`자동 번역됨`**\n{translated_text}"
                await message.channel.send(response)

            # 중국어 메시지 감지
            # if is_message_chinese(message.content):  
            #     # 메시지 전송 권한 확인
            #     permissions = message.channel.permissions_for(message.guild.me)
            #     if not permissions.send_messages:  
            #         return
                
            #     translated_text = await translate_text_deepl(message.content)
            #     response = f"**`중국어 자동 번역됨`**\n{translated_text}"
            #     await message.channel.send(response)

    # 채널별 자동번역 설정 명령어
    @app_commands.command(name="자동번역설정")
    async def auto_translate_setting(self, interaction: discord.Interaction):
        """현재 채널의 자동번역 기능을 설정합니다."""

        # 채널 설정에 현재 채널 ID가 없는 경우 기본값 추가
        channel_id = str(interaction.channel.id)
        if channel_id not in self.channel_settings:
            self.channel_settings[channel_id] = {"host_mid": "", "mention": "", "translation": False, "auto_translate": False}

        # Embed 생성
        embed = create_autotrans_setting_embed(
            interaction.guild, interaction.channel, self.channel_settings
        )
        await interaction.response.send_message(embed=embed, view=ViewAutoTransSetting(self.channel_settings, interaction.channel), ephemeral=True)

# Cog을 봇에 추가하는 함수
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoTranslate(bot))
