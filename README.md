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
 git clone https://github.com/Jrgf27/CanilSeixal.git
 cd CanilSeixal
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
Por defeito, o projeto usa SQLite em desenvolvimento. Para usar PostgreSQL/Aiven, crie um ficheiro `.env` local a partir de `.env.example` e defina `DATABASE_URL` com a connection string da Aiven.

Em Koyeb, adicione `DATABASE_URL` como variável de ambiente/secret com a connection string da Aiven. Não coloque o utilizador ou password diretamente no código.

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
