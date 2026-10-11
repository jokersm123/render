import asyncio
import os
import re
import secrets

import psycopg
from psycopg.rows import dict_row
from werkzeug.security import check_password_hash, generate_password_hash
from nicegui import app, ui


DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
STORAGE_SECRET = os.environ.get('STORAGE_SECRET') or secrets.token_urlsafe(32)
ALLOW_REGISTRATION = os.environ.get('ALLOW_REGISTRATION', 'true').lower() in {'1', 'true', 'yes', 'on'}


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL is not configured')
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_login_at TIMESTAMPTZ
                )
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_uq
                ON users ((LOWER(username)))
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uq
                ON users ((LOWER(email)))
                """
            )


def create_user(username: str, email: str, password: str):
    init_db()
    username = username.strip()
    email = email.strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, is_admin)
                VALUES (
                    %s,
                    %s,
                    %s,
                    NOT EXISTS (SELECT 1 FROM users)
                )
                RETURNING id, username, email, is_admin
                """,
                (username, email, generate_password_hash(password)),
            )
            return cur.fetchone()


def authenticate_user(login: str, password: str):
    init_db()
    login = login.strip()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, email, password_hash, is_active, is_admin
                FROM users
                WHERE LOWER(username) = LOWER(%s)
                   OR LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (login, login),
            )
            user = cur.fetchone()

            if not user or not user['is_active']:
                return None

            if not check_password_hash(user['password_hash'], password):
                return None

            cur.execute(
                'UPDATE users SET last_login_at = NOW() WHERE id = %s',
                (user['id'],),
            )

            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'is_admin': user['is_admin'],
            }


def save_session(user):
    app.storage.user['user_id'] = user['id']
    app.storage.user['username'] = user['username']
    app.storage.user['email'] = user['email']
    app.storage.user['is_admin'] = bool(user['is_admin'])


def logged_in() -> bool:
    return bool(app.storage.user.get('user_id'))


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value.strip()))


# =========================================================
# AUTH UI
# =========================================================

AUTH_HEAD = """
<style>
    body {
        margin: 0;
        min-height: 100vh;
        background: radial-gradient(circle at 80% 10%, rgba(23,148,255,.15), transparent 35%),
                    radial-gradient(circle at 10% 80%, rgba(0,200,180,.10), transparent 35%),
                    #f6f9fd;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #102443;
    }
    .auth-card {
        width: min(430px, calc(100vw - 32px));
        background: rgba(255,255,255,.95);
        border: 1px solid rgba(170,190,220,.40);
        border-radius: 24px;
        padding: 30px;
        box-shadow: 0 22px 70px rgba(40,70,120,.12);
    }
</style>
"""


def auth_shell(title: str, subtitle: str):
    ui.add_head_html(AUTH_HEAD)
    with ui.column().classes('w-full min-h-screen items-center justify-center p-4'):
        with ui.column().classes('auth-card gap-4'):
            ui.label('SHCHERBAKOV').classes('text-xs font-bold tracking-[3px] text-gray-400 self-center')
            ui.label(title).classes('text-3xl font-bold self-center')
            ui.label(subtitle).classes('text-sm text-gray-500 text-center self-center')
            return ui.column().classes('w-full gap-4')


@ui.page('/login')
def login_page():
    if logged_in():
        ui.navigate.to('/')
        return

    ui.add_head_html(AUTH_HEAD)

    with ui.column().classes('w-full min-h-screen items-center justify-center p-4'):
        with ui.column().classes('auth-card gap-4'):
            ui.label('SHCHERBAKOV').classes('text-xs font-bold tracking-[3px] text-gray-400 self-center')
            ui.label('Вхід').classes('text-3xl font-bold self-center')
            ui.label('Увійдіть до Rukopys OCR').classes('text-sm text-gray-500 self-center')

            login_input = ui.input('Логін або email').props('outlined autocomplete=username').classes('w-full')
            password_input = ui.input('Пароль', password=True, password_toggle_button=True).props('outlined autocomplete=current-password').classes('w-full')

            async def do_login():
                if not login_input.value or not password_input.value:
                    ui.notify('Введіть логін та пароль', type='warning')
                    return

                try:
                    user = await asyncio.to_thread(
                        authenticate_user,
                        login_input.value,
                        password_input.value,
                    )
                except Exception as exc:
                    ui.notify(f'Помилка бази даних: {exc}', type='negative')
                    return

                if not user:
                    ui.notify('Невірний логін або пароль', type='negative')
                    return

                save_session(user)
                ui.navigate.to('/')

            ui.button('Увійти', icon='login', on_click=do_login).classes('w-full').props('unelevated color=primary no-caps')

            if ALLOW_REGISTRATION:
                with ui.row().classes('w-full justify-center items-center gap-1'):
                    ui.label('Немає облікового запису?').classes('text-sm text-gray-500')
                    ui.link('Зареєструватися', '/register').classes('text-sm')


@ui.page('/register')
def register_page():
    if logged_in():
        ui.navigate.to('/')
        return

    ui.add_head_html(AUTH_HEAD)

    with ui.column().classes('w-full min-h-screen items-center justify-center p-4'):
        with ui.column().classes('auth-card gap-4'):
            ui.label('SHCHERBAKOV').classes('text-xs font-bold tracking-[3px] text-gray-400 self-center')
            ui.label('Реєстрація').classes('text-3xl font-bold self-center')

            if not ALLOW_REGISTRATION:
                ui.label('Реєстрація тимчасово закрита.').classes('text-sm text-red-500 self-center')
                ui.link('Повернутися до входу', '/login').classes('self-center')
                return

            username_input = ui.input('Логін').props('outlined autocomplete=username maxlength=50').classes('w-full')
            email_input = ui.input('Email').props('outlined type=email autocomplete=email').classes('w-full')
            password_input = ui.input('Пароль', password=True, password_toggle_button=True).props('outlined autocomplete=new-password').classes('w-full')
            repeat_input = ui.input('Повторіть пароль', password=True, password_toggle_button=True).props('outlined autocomplete=new-password').classes('w-full')

            async def do_register():
                username = (username_input.value or '').strip()
                email = (email_input.value or '').strip()
                password = password_input.value or ''
                repeat = repeat_input.value or ''

                if len(username) < 3:
                    ui.notify('Логін має містити щонайменше 3 символи', type='warning')
                    return
                if not valid_email(email):
                    ui.notify('Вкажіть коректний email', type='warning')
                    return
                if len(password) < 8:
                    ui.notify('Пароль має містити щонайменше 8 символів', type='warning')
                    return
                if password != repeat:
                    ui.notify('Паролі не збігаються', type='warning')
                    return

                try:
                    user = await asyncio.to_thread(create_user, username, email, password)
                except psycopg.errors.UniqueViolation:
                    ui.notify('Такий логін або email вже зареєстровано', type='negative')
                    return
                except Exception as exc:
                    ui.notify(f'Помилка бази даних: {exc}', type='negative')
                    return

                save_session(user)
                ui.notify('Реєстрацію завершено', type='positive')
                ui.navigate.to('/')

            ui.button('Створити обліковий запис', icon='person_add', on_click=do_register).classes('w-full').props('unelevated color=primary no-caps')
            ui.link('Вже є обліковий запис? Увійти', '/login').classes('self-center text-sm')


# =========================================================
# MAIN PAGE
# =========================================================

@ui.page('/')
def main_page():
    is_logged_in = logged_in()
    username = app.storage.user.get('username', 'Гість') if is_logged_in else 'Гість'

    state = {
        'uploaded_file': None,
        'uploaded_template': None,
    }

    def logout():
        app.storage.user.clear()
        ui.navigate.to('/')

    def handle_upload(e):
        state['uploaded_file'] = e
        filename = getattr(e, 'name', None)
        if not filename and hasattr(e, 'file'):
            filename = getattr(e.file, 'name', None)
        filename = filename or 'document'
        file_name.set_text(filename)

        if is_logged_in:
            file_status.set_text('Документ готовий до розпізнавання')
            file_status.classes(replace='text-sm text-green-600')
            recognize_button.enable()
        else:
            file_status.set_text('Документ завантажено. Увійдіть, щоб розпізнати.')
            file_status.classes(replace='text-sm text-orange-500')
            recognize_button.disable()

        ui.notify('Документ завантажено', type='positive', position='top')

    def handle_template_upload(e):
        state['uploaded_template'] = e
        filename = getattr(e, 'name', None)
        if not filename and hasattr(e, 'file'):
            filename = getattr(e.file, 'name', None)
        filename = filename or 'template'
        template_file_name.set_text(filename)
        template_status.set_text('Шаблон завантажено')
        template_status.classes(replace='text-sm text-green-600')
        ui.notify('Шаблон документа завантажено', type='positive', position='top')

    async def recognize():
        if not is_logged_in:
            ui.notify('Для розпізнавання спочатку увійдіть', type='warning')
            ui.navigate.to('/login')
            return

        if state['uploaded_file'] is None:
            ui.notify('Спочатку завантажте документ', type='warning')
            return

        recognize_button.disable()
        spinner.set_visibility(True)
        result_block.set_visibility(False)

        # =====================================================
        # ЗДЕСЬ ПОТОМ ПОДКЛЮЧИМ ТВОЙ OCR
        # result = recognize_document(image)
        # =====================================================
        await asyncio.sleep(1.2)

        result_text.value = (
            'Тут буде результат розпізнавання документа.\n\n'
            'Сюди буде підключено doc_ocr_module.'
        )

        spinner.set_visibility(False)
        result_block.set_visibility(True)
        recognize_button.enable()
        ui.notify('Розпізнавання завершено', type='positive')

    ui.add_head_html(
        '''
        <link
            rel="stylesheet"
            href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css"
        >

        <style>

            body {

                margin: 0;

                background:
                    radial-gradient(
                        circle at 80% 10%,
                        rgba(23, 148, 255, 0.14),
                        transparent 35%
                    ),

                    radial-gradient(
                        circle at 10% 80%,
                        rgba(0, 200, 180, 0.09),
                        transparent 35%
                    ),

                    #f6f9fd;

                font-family:
                    Inter,
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    sans-serif;

                color: #102443;
            }


            /* =================================================
               MAIN
            ================================================= */

            .main-wrapper {

                width: 100%;

                max-width: 1280px;

                margin: auto;

                padding-left: 28px;
                padding-right: 28px;
            }


            /* =================================================
               TOP BRAND
            ================================================= */

            .top-brand {
                width: 100%;
                text-align: center;
                padding-top: 16px;
                padding-bottom: 4px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 3px;
                text-transform: uppercase;
                color: #7f8da3;
            }


            /* =================================================
               HEADER
            ================================================= */

            .header {

                height: 78px;

                display: flex;

                align-items: center;

                justify-content: space-between;
            }


            .logo-icon {

                width: 42px;
                height: 42px;

                border-radius: 12px;

                display: flex;

                align-items: center;

                justify-content: center;

                background:
                    linear-gradient(
                        135deg,
                        #006ee6,
                        #00abc1
                    );

                color: white;

                box-shadow:
                    0 7px 24px
                    rgba(0, 100, 210, .20);
            }


            /* =================================================
               HERO
            ================================================= */

            .hero {

                padding-top: 65px;

                padding-bottom: 80px;
            }


            .hero-left {

                width: 54%;
            }


            .hero-upload {

                width: 41%;
            }


            /* =================================================
               TITLE + FORMAT ICONS
            ================================================= */

            .title-row {

                display: flex;

                align-items: center;

                gap: 28px;

                width: 100%;
            }


            .title-box {

                flex: 1;

                min-width: 0;
            }


            .hero-title {

                font-size: clamp(46px, 5.1vw, 74px);

                line-height: 0.98;

                letter-spacing: -3px;

                font-weight: 800;

                color: #10264c;

                white-space: nowrap;
            }


            .hero-gradient {

                background:
                    linear-gradient(
                        90deg,
                        #0878dd,
                        #00a8b5
                    );

                -webkit-background-clip: text;

                -webkit-text-fill-color: transparent;
            }


            /* =================================================
               EXCEL / WORD / PDF
            ================================================= */

            .formats-wrapper {

                display: flex;

                flex-direction: column;

                align-items: center;

                gap: 9px;

                flex-shrink: 0;
            }


            .formats-label {

                font-size: 11px;

                font-weight: 600;

                text-transform: uppercase;

                letter-spacing: 1px;

                color: #9aa8bc;
            }


            .format-icons {

                display: flex;

                gap: 11px;

                align-items: center;
            }


            .format-icon {

                width: 54px;
                height: 54px;

                display: flex;

                align-items: center;

                justify-content: center;

                border-radius: 15px;

                background:
                    rgba(
                        255,
                        255,
                        255,
                        .92
                    );

                font-size: 29px;

                border:
                    1px solid
                    rgba(
                        185,
                        200,
                        220,
                        .35
                    );

                box-shadow:
                    0 8px 28px
                    rgba(
                        20,
                        50,
                        90,
                        .12
                    );

                transition:
                    transform .20s ease,
                    box-shadow .20s ease;
            }


            .format-icon:hover {

                transform:
                    translateY(-5px)
                    scale(1.04);

                box-shadow:
                    0 15px 35px
                    rgba(
                        20,
                        50,
                        90,
                        .18
                    );
            }


            .icon-excel {

                color: #16865b;
            }


            .icon-word {

                color: #2466c3;
            }


            .icon-pdf {

                color: #df3b3b;
            }


            .hero-description {

                max-width: 610px;

                margin-top: 28px;

                font-size: 19px;

                line-height: 1.7;

                color: #66758f;
            }


            /* =================================================
               FEATURE ITEMS
            ================================================= */

            .feature {

                display: flex;

                align-items: center;

                gap: 10px;

                font-size: 14px;

                color: #5d6d87;
            }


            .feature-dot {

                width: 8px;
                height: 8px;

                border-radius: 100%;

                background: #19a4af;
            }


            /* =================================================
               UPLOAD CARD
            ================================================= */

            .upload-card {

                width: 100%;

                background:
                    rgba(
                        255,
                        255,
                        255,
                        0.82
                    );

                backdrop-filter: blur(16px);

                border:
                    1px solid
                    rgba(
                        170,
                        190,
                        220,
                        .35
                    );

                border-radius: 26px;

                padding: 32px;

                box-shadow:
                    0 22px 70px
                    rgba(
                        40,
                        70,
                        120,
                        .11
                    );
            }


            .upload-zone {

                width: 100%;

                border:
                    2px dashed
                    #cbd9e9;

                border-radius: 20px;

                padding:
                    35px
                    20px;

                background:
                    linear-gradient(
                        180deg,
                        rgba(
                            249,
                            252,
                            255,
                            .95
                        ),
                        rgba(
                            244,
                            249,
                            253,
                            .65
                        )
                    );

                transition:
                    all .25s ease;
            }


            .upload-zone:hover {

                border-color: #2389e8;

                background:
                    rgba(
                        237,
                        247,
                        255,
                        .9
                    );
            }


            /* =================================================
               BUTTON
            ================================================= */

            .primary-btn {

                height: 52px;

                border-radius: 14px;

                font-size: 16px;

                font-weight: 600;

                padding:
                    0 28px !important;

                background:
                    linear-gradient(
                        90deg,
                        #0876dc,
                        #00a5b8
                    ) !important;

                box-shadow:
                    0 10px 25px
                    rgba(
                        0,
                        120,
                        210,
                        .20
                    );
            }


            /* =================================================
               TEMPLATE SECTION
            ================================================= */

            .template-card {

                width: 100%;

                margin-top: -34px;
                margin-bottom: 50px;

                display: flex;
                align-items: center;
                justify-content: space-between;

                gap: 28px;

                padding: 26px 30px;

                background:
                    linear-gradient(
                        135deg,
                        rgba(255, 255, 255, .96),
                        rgba(241, 248, 255, .92)
                    );

                border:
                    1px solid rgba(170, 190, 220, .38);

                border-radius: 22px;

                box-shadow:
                    0 14px 42px rgba(40, 70, 120, .08);
            }


            .template-icon {

                width: 54px;
                height: 54px;

                flex-shrink: 0;

                display: flex;
                align-items: center;
                justify-content: center;

                border-radius: 16px;

                background:
                    linear-gradient(
                        135deg,
                        #eef6ff,
                        #e8fbfb
                    );

                color: #0876dc;

                font-size: 28px;
            }


            .template-info {

                flex: 1;
                min-width: 0;
            }


            .template-upload .q-uploader {

                min-width: 210px;
                max-width: 240px;

                border-radius: 14px;

                box-shadow: none;
            }


            .template-upload .q-uploader__header {

                background:
                    linear-gradient(
                        90deg,
                        #10264c,
                        #0876dc
                    );

                border-radius: 14px;
            }


            .scan-card {

                margin-top: 0;
                margin-bottom: 0;

                padding: 26px 30px;
            }


            .scan-icon {

                width: 54px;
                height: 54px;

                flex-shrink: 0;

                display: flex;
                align-items: center;
                justify-content: center;

                border-radius: 16px;

                background:
                    linear-gradient(
                        135deg,
                        #eef6ff,
                        #e8fbfb
                    );

                color: #2f80ed;

                font-size: 28px;
            }


            .scan-info {

                flex: 1;
                min-width: 0;
            }


            .scan-upload .q-uploader {

                min-width: 210px;
                max-width: 240px;

                border-radius: 14px;

                box-shadow: none;
            }


            .scan-upload .q-uploader__header {

                background:
                    linear-gradient(
                        90deg,
                        #2f80ed,
                        #1597d4
                    );

                border-radius: 14px;
            }


            /* =================================================
               RESULT
            ================================================= */

            .result-card {

                margin-top: 26px;

                background: white;

                border:
                    1px solid
                    #e4ebf4;

                border-radius: 22px;

                padding: 26px;

                box-shadow:
                    0 12px 40px
                    rgba(
                        35,
                        60,
                        100,
                        .07
                    );
            }


            /* =================================================
               FOOTER
            ================================================= */

            .footer {

                padding:
                    50px
                    0
                    30px
                    0;

                text-align: center;

                color: #93a0b5;

                font-size: 13px;
            }


            /* =================================================
               TABLET
            ================================================= */

            @media (max-width: 1000px) {

                .hero {

                    padding-top: 35px;
                }


                .hero-left {

                    width: 100%;
                }


                .hero-upload {

                    width: 100%;
                }


                .hero-title {

                    font-size:
                        clamp(
                            46px,
                            8vw,
                            68px
                        );

                    letter-spacing: -2px;
                }


                .upload-card {

                    margin-top: 25px;
                }
            }


            /* =================================================
               PHONE
            ================================================= */

            @media (max-width: 700px) {

                .main-wrapper {

                    padding-left: 18px;

                    padding-right: 18px;
                }


                .header {

                    height: 65px;
                }


                .title-row {

                    flex-direction: column;

                    align-items: flex-start;

                    gap: 23px;
                }


                .hero-title {

                    font-size:
                        clamp(
                            41px,
                            12vw,
                            58px
                        );

                    white-space: normal;

                    line-height: 1.02;
                }


                .formats-wrapper {

                    align-items: flex-start;
                }


                .format-icon {

                    width: 52px;

                    height: 52px;

                    font-size: 27px;
                }


                .hero-description {

                    font-size: 17px;
                }


                .upload-card {

                    padding: 22px;
                }


                .template-card {

                    margin-top: -25px;

                    flex-direction: column;

                    align-items: stretch;

                    padding: 22px;
                }


                .template-upload .q-uploader,
                .scan-upload .q-uploader {

                    width: 100%;
                    max-width: none;
                }


                .scan-card {

                    flex-direction: column;
                    align-items: stretch;
                }

            }

        </style>
        '''
    )


    # =========================================================
    # PAGE
    # =========================================================

    with ui.column().classes(
        'main-wrapper gap-0'
    ):

        # =====================================================
        # TOP BRAND
        # =====================================================

        ui.label(
            'Shcherbakov'
        ).classes(
            'top-brand'
        )


        # =====================================================
        # HEADER
        # =====================================================

        with ui.row().classes(
            'header w-full'
        ):

            with ui.row().classes(
                'items-center gap-3'
            ):

                with ui.element(
                    'div'
                ).classes(
                    'logo-icon'
                ):

                    ui.icon(
                        'document_scanner',
                        size='25px'
                    )

                with ui.column().classes(
                    'gap-0'
                ):

                    ui.label(
                        'Rukopys OCR'
                    ).classes(
                        'text-xl font-bold'
                    )

                    ui.label(
                        'AI Document Recognition'
                    ).classes(
                        'text-xs text-gray-400'
                    )


            with ui.row().classes(
                'items-center gap-3'
            ):
                ui.label(
                    'Українська'
                ).classes(
                    'text-sm text-gray-400'
                )

                if is_logged_in:
                    ui.label(
                        username
                    ).classes(
                        'text-sm font-medium text-gray-600'
                    )

                    ui.button(
                        'Вийти',
                        icon='logout',
                        on_click=logout,
                    ).props(
                        'flat dense no-caps'
                    ).classes(
                        'text-gray-600'
                    )
                else:
                    ui.button(
                        'Увійти',
                        icon='login',
                        on_click=lambda: ui.navigate.to('/login'),
                    ).props(
                        'flat dense no-caps'
                    ).classes(
                        'text-gray-600'
                    )

                    if ALLOW_REGISTRATION:
                        ui.button(
                            'Реєстрація',
                            icon='person_add',
                            on_click=lambda: ui.navigate.to('/register'),
                        ).props(
                            'flat dense no-caps'
                        ).classes(
                            'text-gray-600'
                        )


        # =====================================================
        # HERO
        # =====================================================

        with ui.row().classes(
            'hero w-full items-center justify-between gap-10'
        ):

            # =================================================
            # LEFT
            # =================================================

            with ui.column().classes(
                'hero-left'
            ):


                # TITLE + ICONS
                with ui.row().classes(
                    'title-row'
                ):

                    # TITLE
                    with ui.column().classes(
                        'title-box gap-0'
                    ):

                        ui.label(
                            'Розпізнавання'
                        ).classes(
                            'hero-title'
                        )

                        ui.html(
                            '''
                            <div class="hero-title hero-gradient">
                                рукописних<br>
                                документів
                            </div>
                            '''
                        )


                    # EXCEL / WORD / PDF
                    ui.html(
                        '''
                        <div class="formats-wrapper">

                            <div class="formats-label">
                                Експорт
                            </div>

                            <div class="format-icons">

                                <div
                                    class="format-icon icon-excel"
                                    title="Microsoft Excel"
                                >
                                    <i class="fa-solid fa-file-excel"></i>
                                </div>


                                <div
                                    class="format-icon icon-word"
                                    title="Microsoft Word"
                                >
                                    <i class="fa-solid fa-file-word"></i>
                                </div>


                                <div
                                    class="format-icon icon-pdf"
                                    title="PDF"
                                >
                                    <i class="fa-solid fa-file-pdf"></i>
                                </div>

                            </div>

                        </div>
                        '''
                    )


                # DESCRIPTION
                ui.label(
                    'Перетворюйте рукописні документи '
                    'на структурований цифровий текст '
                    'за допомогою OCR та штучного інтелекту.'
                ).classes(
                    'hero-description'
                )


                # FEATURES
                with ui.row().classes(
                    'gap-6 mt-5 flex-wrap'
                ):

                    for text in [

                        'Рукописний текст',

                        'Українська мова',

                        'OCR + AI',

                    ]:

                        with ui.row().classes(
                            'feature'
                        ):

                            ui.element(
                                'div'
                            ).classes(
                                'feature-dot'
                            )

                            ui.label(text)


            # =================================================
            # RIGHT: SCANNED DOCUMENT
            # =================================================

            with ui.row().classes(
                'hero-upload template-card scan-card'
            ):

                with ui.element(
                    'div'
                ).classes(
                    'scan-icon'
                ):
                    ui.icon(
                        'document_scanner',
                        size='30px'
                    )

                with ui.column().classes(
                    'scan-info gap-1'
                ):
                    ui.label(
                        'Відсканований документ'
                    ).classes(
                        'text-xl font-bold'
                    )

                    ui.label(
                        'Завантажте скан або фото документа для розпізнавання.'
                    ).classes(
                        'text-sm text-gray-500'
                    )

                    file_name = ui.label(
                        'Файл не вибрано'
                    ).classes(
                        'text-sm font-medium mt-1'
                    )

                    file_status = ui.label(
                        'Підтримуються JPEG, PNG та PDF'
                    ).classes(
                        'text-xs text-gray-400'
                    )

                uploader = ui.upload(
                    label='Завантажити скан',
                    auto_upload=True,
                    on_upload=handle_upload,
                ).props(
                    'accept=.jpg,.jpeg,.png,.pdf flat'
                ).classes(
                    'scan-upload'
                )


        # =====================================================
        # TEMPLATE
        # =====================================================

        with ui.row().classes(
            'template-card w-full'
        ):

            with ui.element(
                'div'
            ).classes(
                'template-icon'
            ):
                ui.icon(
                    'description',
                    size='30px'
                )

            with ui.column().classes(
                'template-info gap-1'
            ):
                with ui.row().classes(
                    'items-center gap-2 flex-wrap'
                ):
                    ui.label(
                        'Шаблон документа'
                    ).classes(
                        'text-xl font-bold'
                    )

                    ui.label(
                        'необов’язково'
                    ).classes(
                        'text-xs text-gray-400'
                    )

                ui.label(
                    'Якщо у вас є порожній бланк або еталон документа, '
                    'завантажте його для подальшого зіставлення структури.'
                ).classes(
                    'text-sm text-gray-500'
                )

                template_file_name = ui.label(
                    'Шаблон не вибрано'
                ).classes(
                    'text-sm font-medium mt-1'
                )

                template_status = ui.label(
                    'Підтримуються PDF, зображення, Word та Excel'
                ).classes(
                    'text-xs text-gray-400'
                )

            template_uploader = ui.upload(
                label='Завантажити шаблон',
                auto_upload=True,
                on_upload=handle_template_upload,
            ).props(
                'accept=.jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx flat'
            ).classes(
                'template-upload'
            )


        # =====================================================
        # RECOGNIZE BUTTON
        # =====================================================

        with ui.column().classes(
            'w-full items-center -mt-5 mb-8'
        ):

            recognize_button = ui.button(
                'Розпізнати документ',
                icon='auto_awesome',
                on_click=recognize,
            ).classes(
                'primary-btn w-full max-w-[520px]'
            )

            recognize_button.disable()

            if not is_logged_in:
                ui.label(
                    'Розпізнавання доступне після входу'
                ).classes(
                    'text-xs text-gray-400 mt-1'
                )

            spinner = ui.spinner(
                size='36px'
            ).classes(
                'mt-3'
            )

            spinner.set_visibility(False)


        # =====================================================
        # RESULT
        # =====================================================

        with ui.column().classes(
            'result-card w-full'
        ) as result_block:

            with ui.row().classes(
                'items-center justify-between w-full'
            ):

                with ui.row().classes(
                    'items-center gap-2'
                ):

                    ui.icon(
                        'description'
                    ).classes(
                        'text-blue-500'
                    )

                    ui.label(
                        'Результат розпізнавання'
                    ).classes(
                        'text-xl font-bold'
                    )


                ui.button(
                    icon='content_copy'
                ).props(
                    'flat round'
                )


            result_text = ui.textarea(

                placeholder=
                'Розпізнаний текст з’явиться тут...'

            ).props(

                'outlined autogrow'

            ).classes(

                'w-full mt-3'

            )


        result_block.set_visibility(False)


        # =====================================================
        # FOOTER
        # =====================================================

        with ui.column().classes(
            'footer w-full'
        ):

            ui.label(
                'Rukopys OCR · '
                'Розпізнавання документів '
                'за допомогою AI'
            )


# Try to initialize the schema during startup. The login/register pages will retry if needed.
if DATABASE_URL:
    try:
        init_db()
    except Exception as exc:
        print(f'WARNING: database initialization failed: {exc}')


ui.run(
    host='0.0.0.0',
    port=int(os.environ.get('PORT', '8080')),
    title='Rukopys OCR',
    favicon='📄',
    storage_secret=STORAGE_SECRET,
)
