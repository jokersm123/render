import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage

import psycopg
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from nicegui import app, ui
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = os.environ.get('DATABASE_URL', '')
ALLOW_REGISTRATION = os.environ.get('ALLOW_REGISTRATION', 'true').lower() == 'true'

STORAGE_SECRET = os.environ.get('STORAGE_SECRET', '')
SITE_URL = os.environ.get('SITE_URL', 'https://shcherbakov.website').rstrip('/')

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM = os.environ.get('SMTP_FROM', SMTP_USER)
SMTP_STARTTLS = os.environ.get('SMTP_STARTTLS', 'true').lower() == 'true'
SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'false').lower() == 'true'

EMAIL_VERIFY_MAX_AGE = int(os.environ.get('EMAIL_VERIFY_MAX_AGE', '86400'))

# =========================================================
# HEAD + CSS
# =========================================================

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
    ''',
    shared=True,
)



# =========================================================
# DATABASE / AUTH / EMAIL VERIFICATION
# =========================================================

def db_connect():
    """Open a PostgreSQL connection using Render's DATABASE_URL."""
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL is not configured')
    return psycopg.connect(DATABASE_URL)


def init_db():
    """Create or migrate the users table."""
    if not DATABASE_URL:
        print('WARNING: DATABASE_URL is not configured; authentication DB is unavailable.')
        return

    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    username VARCHAR(80) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    email_verified_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            # Safe migration from the previous version.
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ
            """)
            cur.execute("""
                ALTER TABLE users
                ALTER COLUMN is_active SET DEFAULT FALSE
            """)

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_uq
                ON users (LOWER(username))
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uq
                ON users (LOWER(email))
            """)
        conn.commit()


def get_user(login):
    """Find a user by username or email."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    username,
                    email,
                    password_hash,
                    is_admin,
                    is_active,
                    email_verified_at
                FROM users
                WHERE LOWER(username) = LOWER(%s)
                   OR LOWER(email) = LOWER(%s)
                LIMIT 1
            """, (login, login))
            return cur.fetchone()


def create_user(username, email, password):
    """Create an inactive user. Email confirmation activates the account."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    is_admin,
                    is_active
                )
                VALUES (%s, %s, %s, FALSE, FALSE)
                RETURNING id
            """, (
                username.strip(),
                email.strip().lower(),
                generate_password_hash(password),
            ))
            user_id = cur.fetchone()[0]
        conn.commit()
    return user_id


def make_email_verification_token(user_id, email):
    if not STORAGE_SECRET:
        raise RuntimeError('STORAGE_SECRET is not configured')

    serializer = URLSafeTimedSerializer(
        STORAGE_SECRET,
        salt='rukopys-email-verification',
    )
    return serializer.dumps({
        'user_id': int(user_id),
        'email': email.strip().lower(),
    })


def read_email_verification_token(token):
    if not STORAGE_SECRET:
        raise RuntimeError('STORAGE_SECRET is not configured')

    serializer = URLSafeTimedSerializer(
        STORAGE_SECRET,
        salt='rukopys-email-verification',
    )
    return serializer.loads(
        token,
        max_age=EMAIL_VERIFY_MAX_AGE,
    )


def send_verification_email(user_id, username, email):
    """Send a confirmation link using SMTP configured in Render."""
    if not SMTP_HOST or not SMTP_FROM:
        raise RuntimeError(
            'SMTP is not configured. Set SMTP_HOST, SMTP_PORT, '
            'SMTP_FROM and, if required, SMTP_USER/SMTP_PASSWORD.'
        )

    token = make_email_verification_token(user_id, email)
    verify_url = f'{SITE_URL}/verify-email/{token}'

    message = EmailMessage()
    message['Subject'] = 'Підтвердження реєстрації — Rukopys OCR'
    message['From'] = SMTP_FROM
    message['To'] = email

    message.set_content(
        f'Вітаємо, {username}!\n\n'
        'Щоб завершити реєстрацію в Rukopys OCR, відкрийте посилання:\n\n'
        f'{verify_url}\n\n'
        f'Посилання дійсне {EMAIL_VERIFY_MAX_AGE // 3600} год.\n'
        'Якщо ви не реєструвалися, просто проігноруйте цей лист.'
    )

    message.add_alternative(
        f"""
        <html>
          <body style="font-family:Arial,sans-serif;color:#102443">
            <h2>Rukopys OCR</h2>
            <p>Вітаємо, <b>{username}</b>!</p>
            <p>Щоб завершити реєстрацію, підтвердьте вашу email-адресу.</p>
            <p style="margin:28px 0">
              <a href="{verify_url}"
                 style="background:#0876dc;color:white;text-decoration:none;
                        padding:12px 20px;border-radius:8px;display:inline-block">
                Підтвердити email
              </a>
            </p>
            <p>Посилання дійсне {EMAIL_VERIFY_MAX_AGE // 3600} год.</p>
            <p style="color:#7f8da3;font-size:13px">
              Якщо ви не реєструвалися, просто проігноруйте цей лист.
            </p>
          </body>
        </html>
        """,
        subtype='html',
    )

    context = ssl.create_default_context()

    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
            context=context,
        ) as smtp:
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
        ) as smtp:
            smtp.ehlo()
            if SMTP_STARTTLS:
                smtp.starttls(context=context)
                smtp.ehlo()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)


def activate_user_from_token(token):
    """Verify token and activate the account. First verified user becomes admin."""
    payload = read_email_verification_token(token)

    user_id = int(payload['user_id'])
    email = str(payload['email']).lower()

    with db_connect() as conn:
        with conn.cursor() as cur:
            # Serialize first-admin assignment.
            cur.execute('LOCK TABLE users IN EXCLUSIVE MODE')

            cur.execute("""
                SELECT id, username, email, is_active, is_admin
                FROM users
                WHERE id = %s AND LOWER(email) = LOWER(%s)
                LIMIT 1
            """, (user_id, email))
            user = cur.fetchone()

            if not user:
                raise ValueError('Користувача не знайдено')

            current_id, username, current_email, is_active, is_admin = user

            if not is_active:
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1
                        FROM users
                        WHERE is_admin = TRUE
                          AND is_active = TRUE
                    )
                """)
                admin_exists = cur.fetchone()[0]

                make_admin = not admin_exists

                cur.execute("""
                    UPDATE users
                    SET
                        is_active = TRUE,
                        email_verified_at = NOW(),
                        is_admin = CASE
                            WHEN %s THEN TRUE
                            ELSE is_admin
                        END
                    WHERE id = %s
                    RETURNING is_admin
                """, (make_admin, current_id))
                is_admin = cur.fetchone()[0]

        conn.commit()

    return {
        'user_id': current_id,
        'username': username,
        'email': current_email,
        'is_admin': is_admin,
    }


def require_login():
    """Redirect anonymous users to /login."""
    if not app.storage.user.get('user_id'):
        ui.navigate.to('/login')
        return False
    return True


def auth_page_style():
    ui.add_head_html("""
    <style>
        .auth-shell {
            min-height: 100vh;
        }

        .auth-card {
            width: 100%;
            max-width: 440px;
            padding: 34px;
            border-radius: 24px;
            background: rgba(255, 255, 255, .94);
            border: 1px solid rgba(170, 190, 220, .38);
            box-shadow: 0 22px 70px rgba(40, 70, 120, .11);
            backdrop-filter: blur(16px);
        }

        .auth-btn {
            height: 52px;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 600;
            background: linear-gradient(90deg, #0876dc, #00a5b8) !important;
            box-shadow: 0 10px 25px rgba(0, 120, 210, .20);
        }
    </style>
    """)


@ui.page('/login')
def login_page():
    if app.storage.user.get('user_id'):
        ui.navigate.to('/')
        return

    auth_page_style()

    async def do_login():
        login = (login_input.value or '').strip()
        password = password_input.value or ''

        if not login or not password:
            ui.notify('Введіть логін та пароль', type='warning')
            return

        try:
            user = get_user(login)
        except Exception as exc:
            ui.notify(f'Помилка бази даних: {exc}', type='negative')
            return

        if not user:
            ui.notify('Невірний логін або пароль', type='negative')
            return

        (
            user_id,
            username,
            email,
            password_hash,
            is_admin,
            is_active,
            email_verified_at,
        ) = user

        if not check_password_hash(password_hash, password):
            ui.notify('Невірний логін або пароль', type='negative')
            return

        if not is_active:
            ui.notify(
                'Email ще не підтверджено. Перевірте пошту або надішліть лист повторно.',
                type='warning',
            )
            return

        app.storage.user.update({
            'user_id': user_id,
            'username': username,
            'email': email,
            'is_admin': is_admin,
        })

        ui.navigate.to('/')

    async def resend_confirmation():
        login = (login_input.value or '').strip()
        password = password_input.value or ''

        if not login or not password:
            ui.notify(
                'Введіть логін/email і пароль, потім повторіть відправлення',
                type='warning',
            )
            return

        try:
            user = get_user(login)
            if not user:
                ui.notify('Невірний логін або пароль', type='negative')
                return

            (
                user_id,
                username,
                email,
                password_hash,
                is_admin,
                is_active,
                email_verified_at,
            ) = user

            if not check_password_hash(password_hash, password):
                ui.notify('Невірний логін або пароль', type='negative')
                return

            if is_active:
                ui.notify('Email вже підтверджено', type='positive')
                return

            await asyncio.to_thread(
                send_verification_email,
                user_id,
                username,
                email,
            )

            ui.notify(
                'Лист підтвердження надіслано повторно',
                type='positive',
            )
        except Exception as exc:
            ui.notify(
                f'Не вдалося надіслати лист: {exc}',
                type='negative',
            )

    with ui.column().classes(
        'auth-shell w-full items-center justify-center px-5'
    ):
        with ui.column().classes('auth-card gap-4'):

            ui.label(
                'Shcherbakov'
            ).classes(
                'w-full text-center text-sm font-bold '
                'tracking-[3px] uppercase text-gray-500'
            )

            ui.label(
                'Rukopys OCR'
            ).classes(
                'text-3xl font-bold w-full text-center'
            )

            ui.label(
                'Вхід до системи'
            ).classes(
                'text-gray-500 w-full text-center mb-3'
            )

            if not DATABASE_URL:
                ui.label(
                    'DATABASE_URL не налаштовано'
                ).classes(
                    'text-red-500 text-sm w-full text-center'
                )

            login_input = ui.input(
                'Логін або email'
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            password_input = ui.input(
                'Пароль',
                password=True,
                password_toggle_button=True,
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            ui.button(
                'Увійти',
                icon='login',
                on_click=do_login,
            ).classes(
                'auth-btn w-full'
            )

            ui.button(
                'Надіслати підтвердження повторно',
                icon='mail',
                on_click=resend_confirmation,
            ).props(
                'flat'
            ).classes(
                'w-full'
            )

            if ALLOW_REGISTRATION:
                ui.button(
                    'Реєстрація',
                    icon='person_add',
                    on_click=lambda: ui.navigate.to('/register'),
                ).props(
                    'flat'
                ).classes(
                    'w-full'
                )


@ui.page('/register')
def register_page():
    if not ALLOW_REGISTRATION:
        ui.navigate.to('/login')
        return

    if app.storage.user.get('user_id'):
        ui.navigate.to('/')
        return

    auth_page_style()

    async def do_register():
        username = (username_input.value or '').strip()
        email = (email_input.value or '').strip()
        password = password_input.value or ''
        password2 = password2_input.value or ''

        if len(username) < 3:
            ui.notify(
                'Логін має містити щонайменше 3 символи',
                type='warning',
            )
            return

        if len(username) > 80:
            ui.notify('Логін занадто довгий', type='warning')
            return

        if '@' not in email or '.' not in email.split('@')[-1]:
            ui.notify('Вкажіть коректний email', type='warning')
            return

        if len(email) > 255:
            ui.notify('Email занадто довгий', type='warning')
            return

        if len(password) < 8:
            ui.notify(
                'Пароль має містити щонайменше 8 символів',
                type='warning',
            )
            return

        if password != password2:
            ui.notify('Паролі не збігаються', type='warning')
            return

        try:
            user_id = create_user(
                username,
                email,
                password,
            )

            await asyncio.to_thread(
                send_verification_email,
                user_id,
                username,
                email,
            )

        except psycopg.errors.UniqueViolation:
            ui.notify(
                'Такий логін або email вже існує',
                type='negative',
            )
            return
        except Exception as exc:
            ui.notify(
                f'Реєстрацію створено, але лист не надіслано: {exc}',
                type='negative',
            )
            return

        ui.notify(
            'Реєстрацію створено. Перевірте email та підтвердьте адресу.',
            type='positive',
        )
        ui.navigate.to('/login')

    with ui.column().classes(
        'auth-shell w-full items-center justify-center px-5'
    ):
        with ui.column().classes('auth-card gap-4'):

            ui.label(
                'Shcherbakov'
            ).classes(
                'w-full text-center text-sm font-bold '
                'tracking-[3px] uppercase text-gray-500'
            )

            ui.label(
                'Реєстрація'
            ).classes(
                'text-3xl font-bold w-full text-center'
            )

            ui.label(
                'Після реєстрації ми надішлемо лист для підтвердження email'
            ).classes(
                'text-gray-500 w-full text-center mb-3'
            )

            username_input = ui.input(
                'Логін'
            ).props(
                'outlined maxlength=80'
            ).classes(
                'w-full'
            )

            email_input = ui.input(
                'Email'
            ).props(
                'outlined type=email maxlength=255'
            ).classes(
                'w-full'
            )

            password_input = ui.input(
                'Пароль',
                password=True,
                password_toggle_button=True,
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            password2_input = ui.input(
                'Повторіть пароль',
                password=True,
                password_toggle_button=True,
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            ui.button(
                'Зареєструватися',
                icon='person_add',
                on_click=do_register,
            ).classes(
                'auth-btn w-full'
            )

            ui.button(
                'Повернутися до входу',
                on_click=lambda: ui.navigate.to('/login'),
            ).props(
                'flat'
            ).classes(
                'w-full'
            )


@ui.page('/verify-email/{token}')
def verify_email_page(token: str):
    auth_page_style()

    status = {
        'ok': False,
        'title': 'Підтвердження email',
        'message': '',
    }

    try:
        user = activate_user_from_token(token)

        app.storage.user.update({
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'is_admin': user['is_admin'],
        })

        status['ok'] = True
        status['title'] = 'Email підтверджено'
        status['message'] = (
            'Реєстрацію завершено. Тепер ви можете користуватися Rukopys OCR.'
        )

    except SignatureExpired:
        status['message'] = (
            'Термін дії посилання минув. '
            'Поверніться на сторінку входу та надішліть підтвердження повторно.'
        )
    except BadSignature:
        status['message'] = 'Посилання підтвердження недійсне.'
    except Exception as exc:
        status['message'] = f'Не вдалося підтвердити email: {exc}'

    with ui.column().classes(
        'auth-shell w-full items-center justify-center px-5'
    ):
        with ui.column().classes('auth-card gap-4 items-center'):

            ui.icon(
                'verified' if status['ok'] else 'error',
                size='54px',
            ).classes(
                'text-green-600' if status['ok'] else 'text-red-500'
            )

            ui.label(
                status['title']
            ).classes(
                'text-3xl font-bold text-center'
            )

            ui.label(
                status['message']
            ).classes(
                'text-gray-500 text-center'
            )

            ui.button(
                'Перейти до системи' if status['ok'] else 'Повернутися до входу',
                on_click=lambda: ui.navigate.to(
                    '/' if status['ok'] else '/login'
                ),
            ).classes(
                'auth-btn w-full mt-2'
            )


@ui.page('/logout')
def logout_page():
    app.storage.user.clear()
    ui.navigate.to('/login')


# =========================================================
# PROTECTED MAIN PAGE
# =========================================================

@ui.page('/')
def main_page():
    if not require_login():
        return

    state = {
        'uploaded_file': None,
        'uploaded_template': None,
    }

    def handle_upload(e):
        state['uploaded_file'] = e

        filename = getattr(e, 'name', None)

        if not filename and hasattr(e, 'file'):
            filename = getattr(e.file, 'name', None)

        filename = filename or 'document'

        file_name.set_text(filename)

        file_status.set_text(
            'Документ готовий до розпізнавання'
        )

        file_status.classes(
            replace='text-sm text-green-600'
        )

        recognize_button.enable()

        ui.notify(
            'Документ завантажено',
            type='positive',
            position='top',
        )

    def handle_template_upload(e):
        state['uploaded_template'] = e

        filename = getattr(e, 'name', None)

        if not filename and hasattr(e, 'file'):
            filename = getattr(e.file, 'name', None)

        filename = filename or 'template'

        template_file_name.set_text(filename)

        template_status.set_text(
            'Шаблон завантажено'
        )

        template_status.classes(
            replace='text-sm text-green-600'
        )

        ui.notify(
            'Шаблон документа завантажено',
            type='positive',
            position='top',
        )

    async def recognize():
        if state['uploaded_file'] is None:
            ui.notify(
                'Спочатку завантажте документ',
                type='warning',
            )
            return

        recognize_button.disable()

        spinner.set_visibility(True)
        result_block.set_visibility(False)

        # =====================================================
        # ЗДЕСЬ ПОТОМ ПОДКЛЮЧИМ ТВОЙ OCR
        #
        # result = recognize_document(image)
        #
        # =====================================================

        await asyncio.sleep(1.2)

        result_text.value = (
            'Тут буде результат розпізнавання документа.\n\n'
            'Сюди буде підключено doc_ocr_module.'
        )

        spinner.set_visibility(False)
        result_block.set_visibility(True)

        recognize_button.enable()

        ui.notify(
            'Розпізнавання завершено',
            type='positive',
        )

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
                    'text-sm text-gray-500'
                )

                ui.label(
                    app.storage.user.get('username', '')
                ).classes(
                    'text-sm font-medium text-gray-600'
                )

                ui.button(
                    icon='logout',
                    on_click=lambda: ui.navigate.to('/logout'),
                ).props(
                    'flat round dense'
                ).tooltip(
                    'Вийти'
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


# =========================================================
# RUN
# =========================================================

init_db()

ui.run(
    host='0.0.0.0',
    port=int(os.environ.get('PORT', '8080')),
    title='Rukopys OCR',
    favicon='📄',
    storage_secret=STORAGE_SECRET or 'CHANGE-ME-IN-RENDER',
)
