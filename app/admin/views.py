from sqladmin import ModelView, BaseView, expose
from wtforms import DecimalField, IntegerField, SelectField, TextAreaField
from app.config import Config
from app.cruds.bot_user_message import get_message_history
from app.database import AsyncSessionLocal
from app.models.bot_user_message import BotUserMessage
from app.models.bot_user import BotUser
from markupsafe import Markup
from app.models.source_faq import SourceFaq
from app.models.source_yml import SourceYml
from app.models.system_setting import SystemSetting

class SystemSettingAdmin(ModelView, model=SystemSetting):
    can_delete = False
    can_create = False
    can_export = False
    list_template = "admin/custom_list.html" 

    name_plural = name = "Системные настройки"
    icon = "fa-solid fa-gears"
    column_default_sort = ("sort", True)

    column_list = [SystemSetting.description, SystemSetting.value]

    def format_value(model, context):
        # Если значение пустое или None, возвращаем пустую строку
        if not model.value:
            return ""
        
        max_length = 50  # Максимальное количество символов для отображения
        
        if len(model.value) > max_length:
            return f"{model.value[:max_length]}..."
        return model.value

    # Привязываем наш форматтер к колонке 'value'
    column_formatters = {
        "value": format_value
    }
    
    column_labels = {
        "value": "значение",
        "description": "описание"
    }

    form_columns = [SystemSetting.value]

    page_size = 30 

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        original_init = form_class.__init__
        
        def custom_init(form_self, *args, **kwargs):
            original_init(form_self, *args, **kwargs)
            
            obj = kwargs.get("obj")
            if not obj:
                return

            # Выносим общую логику определения названия поля
            field_label = obj.description if obj.description else "значение"
            unbound_field = None
            current_value = obj.value

            if obj and obj.key in ["assistant.scope"]:
                # Список вариантов для селекта
                choices = [
                    ("GIGACHAT_API_PERS", "GIGACHAT_API_PERS"),
                    ("GIGACHAT_API_B2B", "GIGACHAT_API_B2B"),
                    ("GIGACHAT_API_CORP", "GIGACHAT_API_CORP")
                ]
                
                # 3. Создаем связанное поле (Bound Field) через bind() самой формы
                unbound_field = SelectField(label=field_label, choices=choices, render_kw={"class": "form-control form-select"})


            elif obj and obj.key in ["assistant.model", "parser.model"]:
                # Список вариантов для селекта
                choices = [
                    ("GigaChat-2", "[ GigaChat-2 ] быстрая и легкая версия, отлично подходит для простых повседневных задач, ответов на вопросы и общения."),
                    ("GigaChat-2-Pro", "[ GigaChat-2-Pro ] усовершенствованная, сбалансированная модель для ресурсоемких задач. Справляется со сложными текстами, кодом и аналитикой."),
                    ("GigaChat-2-Max", "[ GigaChat-2-Max ] самая мощная и функциональная флагманская модель Сбера для решения наиболее масштабных и сложных задач.")
                ]
                
                # 3. Создаем связанное поле (Bound Field) через bind() самой формы
                unbound_field = SelectField(label=field_label, choices=choices, render_kw={"class": "form-control form-select"})

            elif obj.key in [
                "assistant.max_tokens",
                "assistant.ask_delay", 
                "assistant.history_message_count",
                "faiss.faq.max_score",
                "faiss.faq.k",
                "faiss.faq.cache_time",
                "faiss.yml.max_score",
                "faiss.yml.k",
                "faiss.yml.fetch_k",
                "faiss.yml.cache_time",
                "sync.interval",
                ]:
                unbound_field = IntegerField(
                    label=field_label,
                    render_kw={
                        "class": "form-control", 
                        "type": "number", 
                        "step": "1",
                        "min": "0"  # Опционально: запрещаем вводить отрицательные числа
                    }
                )
                if current_value:
                    current_value = int(current_value)

            elif obj.key in [
                "assistant.temperature", 
                "assistant.top_p", 
                "parser.temperature", 
                "parser.top_p"
                ]:
                unbound_field = DecimalField(
                    label=field_label,
                    places=2,  # Округлять до 2 знаков после запятой
                    render_kw={
                        "class": "form-control",
                        "type": "number",
                        "min": "0",
                        "max": "1",
                        "step": "0.05" 
                    }
                )
                if current_value:
                    current_value = float(current_value)

            else:
                unbound_field = TextAreaField(
                    label=field_label,
                    render_kw={
                        "class": "form-control",
                        "rows": "20",  # Начальная высота в строках
                        "style": "resize: none; overflow-y: hidden;", # Запрещаем ручной ресайз мышкой и скрываем скролл
                        # Самая магия: при вводе сбрасываем высоту и ставим равной scrollHeight
                        "oninput": "this.style.height = 'auto'; this.style.height = this.scrollHeight + 'px';"
                    }
                )

            if unbound_field:
                # 3. Создаем связанное поле (Bound Field) через bind() самой формы
                bound_field = unbound_field.bind(form_self, name="value")
                # 4. Передаем в поле актуальное значение (из POST-запроса или из БД)
                # kwargs.get("formdata") содержит отправленные юзером данные при сабмите
                bound_field.process(kwargs.get("formdata"), current_value)
                # 5. Подменяем поле в инстансе формы
                form_self.value = bound_field
                form_self._fields["value"] = bound_field

        form_class.__init__ = custom_init
        return form_class



class BotUserAdmin(ModelView, model=BotUser):
    name_plural = name = "Сессии пользователей"
    icon = "fa-solid fa-users"
    can_create = False
    can_export = False

    column_list = [BotUser.chat_id, BotUser.name]
    form_columns = [BotUser.chat_id, BotUser.name]


class BotUserMessageAdmin(ModelView, model=BotUserMessage):
    name_plural = name = "История сообщений"
    icon = "fa-solid fa-comments"
    can_create = False
    can_export = False

    column_labels = {
        BotUserMessage.chat_id: "id чата",
        BotUserMessage.type: "тип сообщения",
        BotUserMessage.text: "текст сообщения",
        BotUserMessage.tokens: "Токены",
        BotUserMessage.created_at: "время создания"
    }
    column_list = [BotUserMessage.tokens, BotUserMessage.created_at, BotUserMessage.chat_id, BotUserMessage.type, BotUserMessage.text]
    form_columns = [BotUserMessage.chat_id, BotUserMessage.type, BotUserMessage.text]
    column_searchable_list = [BotUserMessage.type, BotUserMessage.chat_id]
    
    column_sortable_list = [BotUserMessage.id]
    column_default_sort = ("id", True)

    column_formatters = {
        "text": lambda m, a: Markup(m.text.replace("\n\n", "<br>").replace("\n", "<br>")) if m.text else ""
    }
    
class ChatAssistantAdmin(BaseView):
    name = "Ассистент в чате"
    icon = "fa-solid fa-comment"

    @expose("/chat", methods=["GET"])
    async def chat_page(self, request):
        content = ""

        async with AsyncSessionLocal() as session:
            history = await get_message_history(session, chat_id="admin_panel", limit=10)
        if history:
            for message in history:
                text = message.text.split("Вопрос:")
                text_clean = text[1] if len(text) > 1 else message.text
                #text_clean = clean_response_for_chat(text_clean)

                content += f"""<div class="message {"user" if message.type.name == "HUMAN" else "bot"}">{text_clean}</div>"""
        else:
            content = "<div class=\"message bot\">Привет! Чем я могу помочь?</div>"

        return await self.templates.TemplateResponse(
            request, 
            #"admin/chat_assistant.html",
            "admin/widget.html",
            context={"content": Markup(content), "domain": Config.DOMAIN}
        )
    


class SourceYmlAdmin(ModelView, model=SourceYml):
    #category = "Источники знаний"
    name_plural = name = "Знания: Yml-файлы"

    list_template = "admin/custom_list.html" 

    icon = "fa-solid fa-brain"
    column_list = [SourceYml.active, SourceYml.id, SourceYml.url]

    column_labels = {
        SourceYml.active: "Активность",
        SourceYml.id: "id",
        SourceYml.url: "Ссылка",
    }

    form_columns = [
        SourceYml.active,
        SourceYml.url,
    ]

class SourceFaqAdmin(ModelView, model=SourceFaq):
    #category = "Источники знаний"
    name_plural = name = "Знания: HTML-FAQ"

    list_template = "admin/custom_list.html" 

    icon = "fa-solid fa-brain"
    column_list = [SourceFaq.active, SourceFaq.id, SourceFaq.url]

    column_labels = {
        SourceFaq.active: "Активность",
        SourceFaq.id: "id",
        SourceFaq.url: "Ссылка",
    }

    form_columns = [
        SourceFaq.active,
        SourceFaq.url,
        SourceFaq.selector_question,
        SourceFaq.selector_answer,
    ]



    