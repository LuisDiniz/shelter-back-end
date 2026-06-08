## 🚀 Tecnologias Utilizadas

- Python 3.10 ou acima

## 📜 Pré-requisitos

Antes de iniciar, certifique-se de ter instalado:

- [Python](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/) Normalmente é instalado em conjunto com Python.
- [Virtualenv](https://virtualenv.pypa.io/en/latest/) Não necessário mas bom de ter para desenvolvimento.

## ⚙️ Como Correr o Projeto

### 1️⃣ Clonar o Repositório
```sh
 git clone https://github.com/LuisDiniz/shelter-back-end
 cd shelter-back-end
```

### 2️⃣ Criar e Ativar um Ambiente Virtual (Caso esteja a ser usado)

**Windows:**
```sh
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```sh
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Instalar as Dependências
```sh
pip install -r requirements.txt
```

### 4️⃣ Configurar a Base de Dados
Por defeito, o projeto usa SQLite em desenvolvimento. Para usar PostgreSQL/Aiven, crie um ficheiro `.env` local a partir de `.env.example` e defina `DATABASE_URL` com a connection string da base de dados.

Para permitir upload de imagens de animais para Cloudinary, configure também `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` e `CLOUDINARY_API_SECRET`. Opcionalmente, ajuste `CLOUDINARY_ANIMAL_FOLDER` e `CLOUDINARY_MAX_IMAGE_BYTES`.

A API guarda o URL final devolvido pela Cloudinary na tabela de imagens do animal e expõe o primeiro URL como `image_url` por compatibilidade.

```sh
python manage.py makemigrations
python manage.py migrate
```

### 5️⃣ Criar um Superusuário
```sh
python manage.py createsuperuser
```
Siga as instruções para definir e-mail e senha.

### 6️⃣ Iniciar o Servidor Local
```sh
python manage.py runserver
```

O projeto vai estar disponível em: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
