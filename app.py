from flask import Flask, render_template_string

app = Flask(__name__)

PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>shcherbakov.website</title>

    <style>
        html, body {
            margin: 0;
            width: 100%;
            height: 100%;
        }

        body {
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;

            background: #000;
            color: #fff;
            font-family: Arial, sans-serif;
        }

        .picture {
            position: absolute;

            left: 50%;
            top: calc(50% - 210px);

            transform: translate(-50%, -50%);

            width: 220px;
            max-width: 70vw;
            height: auto;
        }

        h1 {
            font-size: clamp(40px, 8vw, 120px);
            text-align: center;
            margin: 20px;
        }
    </style>
</head>

<body>

    <img
        class="picture"
        src="/static/picture.png"
        alt=""
    >

    <h1>Не kot56superlong.com</h1>

</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
