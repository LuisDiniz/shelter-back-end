from django.db import migrations


SEED_ANIMALS = [
    {
        "name": "Léo",
        "tipo": "cat",
        "gender": "male",
        "idade": 7,
        "descricao": (
            "Léo tem um feitio muito particular gosta de estar por perto, a observar-nos, "
            "é muito guloso e anda atrás dos biscoitos mas não é muito dado a festas. "
            "Evita o contato conosco ainda que esteja sempre atento a nós. Já com uma certa "
            "idade, gostas de sestas longas e de apanhar banhos de sol."
        ),
        "raca": "Europeu",
        "image_url": "https://res.cloudinary.com/dlqmc28to/image/upload/c_crop,g_custom/Leo_ywbenz.jpg",
    },
    {
        "name": "Evaristo",
        "tipo": "cat",
        "gender": "male",
        "idade": 8,
        "descricao": (
            "O Evaristo é um lindo e gorducho gatão. Foi adotado em Agosto de 2025, "
            "de quem fomos sempre tendo noticias até ao final do ano de 2025, mas "
            "infelizmente foi devolvido para a associação magro, pelo branco e olhar "
            "triste e teve que ficar internado. O Evaristo é um menino forte temos a "
            "certeza que vai recuperar."
        ),
        "raca": "Europeu",
        "image_url": "https://res.cloudinary.com/dlqmc28to/image/upload/v1773878172/Evaristo2_eywoqt.jpg",
    },
    {
        "name": "Dentuças",
        "tipo": "cat",
        "gender": "female",
        "idade": 7,
        "descricao": (
            "Dentuças foi diagnosticada com carcinoma na mandíbula. Dentuças mantém a "
            "doença controlada com medicação, segue ativa, brincalhona e cheia de vida, "
            "lembrando a todos que viver com esperança é uma forma de vencer todos os dias."
        ),
        "raca": "Europeu",
        "image_url": "https://res.cloudinary.com/dlqmc28to/image/upload/v1765875774/Dentuc%CC%A7as_egitih.jpg",
    },
    {
        "name": "Malvadinha",
        "tipo": "cat",
        "gender": "female",
        "idade": 8,
        "descricao": (
            "Malvadinha é uma gata medrosa e não gosta de muito contacto direto, ela ainda "
            "precisa ser conquistada. Malvadinha não liga muito para os biscoitos mas não "
            "resistem a um bom patê. Ela é um dos animais que já estão no abrigo há algum "
            "tempo também."
        ),
        "raca": "Europeu",
        "image_url": "https://res.cloudinary.com/dlqmc28to/image/upload/c_crop,g_custom/v1765832945/Malvadinha_wi7n6z.jpg",
    },
    {
        "name": "Palhacinho",
        "tipo": "cat",
        "gender": "male",
        "idade": 9,
        "descricao": (
            "Palhacinho enfrenta um linfoma nos intestinos, faz quimioterapia de 15 em 15 "
            "dias e toma corticoide diariamente. Mesmo nos dias mais frágeis, mantém o "
            "olhar brilhante e a vontade de dar alegria a quem está por perto. É a prova "
            "que coragem e ternura podem andar de mãos dadas."
        ),
        "raca": "Europeu",
        "image_url": "https://res.cloudinary.com/dlqmc28to/image/upload/IMG_1655_kqeqel",
    },
    {
        "name": "Manny",
        "tipo": "cat",
        "gender": "male",
        "idade": 5,
        "descricao": (
            "Manny tem um problema ósseo numa patinha que pode levar à amputação. Ainda "
            "assim, não perde a alegria nem a vontade de brincar. Mostra que a verdadeira "
            "coragem é seguir em frente, mesmo diante das incertezas."
        ),
        "raca": "Europeu",
        "image_url": "https://res.cloudinary.com/dlqmc28to/image/upload/v1771244812/IMG_1657_gsuvtg.jpg",
    },
    {
        "name": "Malhadinha",
        "tipo": "cat",
        "gender": "female",
        "idade": 6,
        "descricao": (
            "Malhadinha é muito medrosa e não gosta muito de festinhas, mas não recusa um "
            "patê. Malhadinha já está connosco há algum tempo a espera de uma família."
        ),
        "raca": "Europeu",
        "image_url": "https://res.cloudinary.com/dlqmc28to/image/upload/v1771370818/Malhadinha_h00xmb.jpg",
    },
]


def seed_animals(apps, schema_editor):
    animal_model = apps.get_model("animais", "Animal")

    for animal_data in SEED_ANIMALS:
        if animal_model.objects.filter(name=animal_data["name"]).exists():
            continue

        animal_model.objects.create(
            cor="N/A",
            pelo="N/A",
            porte="N/A",
            informacao_extra="",
            comportamento_pessoas="",
            comportamento_animais="",
            medical_history="",
            vaccinations="",
            **animal_data,
        )


def remove_seed_animals(apps, schema_editor):
    animal_model = apps.get_model("animais", "Animal")
    seed_image_urls = [animal["image_url"] for animal in SEED_ANIMALS]

    animal_model.objects.filter(image_url__in=seed_image_urls).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("animais", "0003_animal_api_fields"),
    ]

    operations = [
        migrations.RunPython(seed_animals, remove_seed_animals),
    ]
