import os
import json
from datetime import datetime
from urllib.parse import quote
from sqladmin import ModelView, BaseView, expose
from wtforms import DecimalField, IntegerField, SelectField, TextAreaField
from app.config import Config
from app.cruds.bot_user_message import get_message_history
from app.database import AsyncSessionLocal
from app.models.bot_user_message import BotUserMessage, MessageType
from app.models.bot_user import BotUser
from markupsafe import Markup
from app.models.faq_extra import FaqExtra
from app.models.source_faq import SourceFaq
from app.models.source_yml import SourceYml
from app.models.system_setting import SystemSetting
from app import CLIENT_CACHE_DIR
from app.state import sync_event
from app.utils.common import get_rag_cache_path, normalize_answer

def _date_format(value=None):
    if not value:
        return ""
    now = datetime.now()
    if value.date() == now.date():
        return value.strftime("%H:%M")
    if value.year == now.year:
        return value.strftime("%d.%m %H:%M")
    return value.strftime("%d.%m.%Y %H:%M")

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

    page_size = 50 

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
                "assistant.ask_limit", 
                "assistant.ask_interval", 
                "assistant.history_message_count",
                "faiss.faq.max_score",
                "faiss.faq.k",
                "faiss.faq.cache_time",
                "faiss.yml.max_score",
                "faiss.yml.k",
                "faiss.yml.fetch_k",
                "faiss.yml.cache_time",
                "sync.interval",
                "ask.max_concurrent_requests",
                "ask.max_queue_size",
                "history.delete_interval",
                "history.ttl_chat",
                "history.ttl_chat_view",
                "history.count_chat_view"
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


def _format_message_text(m):
    if not m.text:
        return ""
    if m.type == MessageType.AI:
        json_str = normalize_answer(m.text)
        try:
            parsed = json.loads(json_str)
            return Markup(f"<pre style='white-space:pre-wrap;margin:0;color:#555;font-size:0.85em;background:#f8f9fa;border-radius:6px;padding:6px'>{json.dumps(parsed, indent=2, ensure_ascii=False)}</pre>")
        except (json.JSONDecodeError, ValueError):
            #return Markup(f"<pre style='white-space:pre-wrap;margin:0;color:#555;font-size:0.85em;background:#f8f9fa;border-radius:6px;padding:6px'>{json_str}</pre>")
            pass
    text = m.text.replace("\n\n", "<br>").replace("\n", "<br>")
    if m.type == MessageType.HUMAN:
        return Markup(
            f'<span style="background:#aced9d;border-radius:6px;padding:2px 6px;display:inline-block">{text}</span>'
            f' <a title="Добавить вопрос в FAQ и написать ответ" href="/admin/faq-extra/create?question={quote(m.text or "")}" '
            f'class="btn btn-sm btn-outline-primary" '
            f'style="white-space:nowrap;font-size:0.75rem;padding:2px 8px;border-radius:12px" '
            f'onclick="event.stopPropagation()">'
            f'<i class="fa-solid fa-plus me-1"></i>доп.FAQ</a>'
        )


class BotUserMessageAdmin(ModelView, model=BotUserMessage):
    name_plural = name = "История сообщений"
    icon = "fa-solid fa-comments"
    can_create = False
    can_export = False

    page_size = 30 

    #column_list = [BotUserMessage.tokens, "add_to_faq", BotUserMessage.text, BotUserMessage.chat_id]
    column_list = [BotUserMessage.tokens, BotUserMessage.type, BotUserMessage.text, BotUserMessage.chat_id]
    form_columns = [BotUserMessage.chat_id, BotUserMessage.type, BotUserMessage.text]
    column_searchable_list = [BotUserMessage.type, BotUserMessage.chat_id]

    column_labels = {
        BotUserMessage.chat_id: "Чат",
        BotUserMessage.type: "Отправитель",
        BotUserMessage.text: "Текст сообщения",
        BotUserMessage.tokens: "Токены",
        BotUserMessage.created_at: "время создания",
        "add_to_faq": "",
    }

    column_sortable_list = [BotUserMessage.id]
    column_default_sort = ("id", True)

    column_formatters = {
        "text": lambda m, a: _format_message_text(m),
        "chat_id": lambda m, a: Markup(f'<a title="Все сообщения диалога №{m.chat_id}" href="/admin/bot-user-message/list?search={m.chat_id}"><i class="fa-solid fa-comment"></i></a>'),
        "type": lambda m, a: 
            Markup(f'<div class="text-center"><i class="fa-solid fa-question" title="AI"></i><br><span class="small">{_date_format(m.created_at)}</span></span></div>')
            if m.type == MessageType.HUMAN else (
                Markup(f'<div class="text-center"><i class="fa-solid fa-robot" title="AI"></i><br><span class="small">{_date_format(m.created_at)}</span></span></div>') if m.type == MessageType.AI else ""
            )
    }


    """Markup(
            f'<a title="Добавить вопрос в FAQ и написать ответ" href="/admin/faq-extra/create?question={quote(m.text or "")}" '
            f'class="btn btn-sm btn-outline-primary" '
            f'style="white-space:nowrap;font-size:0.75rem;padding:2px 8px;border-radius:12px" '
            f'onclick="event.stopPropagation()">'
            f'<i class="fa-solid fa-plus me-1"></i>доп.FAQ</a>'
        )"""
    
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
    


class FaqExtraAdmin(ModelView, model=FaqExtra):
    name_plural = name = "Знания: Доп. FAQ"
    icon = "fa-solid fa-brain"
    can_export = False
    create_template = "admin/faqextra_create.html"

    column_list = [FaqExtra.id, FaqExtra.question, FaqExtra.answer]
    column_labels = {
        FaqExtra.id: "id",
        FaqExtra.question: "Вопрос",
        FaqExtra.answer: "Ответ",
    }
    column_searchable_list = [FaqExtra.question]
    column_default_sort = ("id", True)

    form_columns = [FaqExtra.question, FaqExtra.answer]

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.question = TextAreaField(
            label="Вопрос",
            render_kw={"class": "form-control", "rows": "3",
                       "style": "resize: none; overflow-y: hidden;",
                       "oninput": "this.style.height = 'auto'; this.style.height = this.scrollHeight + 'px';"}
        )
        form_class.answer = TextAreaField(
            label="Ответ",
            render_kw={"class": "form-control", "rows": "6",
                       "style": "resize: none; overflow-y: hidden;",
                       "oninput": "this.style.height = 'auto'; this.style.height = this.scrollHeight + 'px';"}
        )
        return form_class
    
    async def after_model_delete(self, model, _request):
        sync_event.set()

    async def after_model_change(self, _data, model, _is_created, _request):
        sync_event.set()
        
    async def after_model_add(self, model, _request):
        sync_event.set()


class _SourceAdminMixin:
    @staticmethod
    def _invalidate_cache(model):
        cache_path = get_rag_cache_path({"url": model.url}, CLIENT_CACHE_DIR)
        if os.path.exists(cache_path):
            os.remove(cache_path)

    async def after_model_change(self, _data, model, _is_created, _request):
        if not model.active:
            self._invalidate_cache(model)
        sync_event.set()


    async def after_model_delete(self, model, _request):
        self._invalidate_cache(model)
        sync_event.set()


class SourceYmlAdmin(_SourceAdminMixin, ModelView, model=SourceYml):
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


class SourceFaqAdmin(_SourceAdminMixin, ModelView, model=SourceFaq):
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



    