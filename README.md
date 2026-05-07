# Site de Pesquisa de Marketing

Este é um site responsivo baseado no sistema de pesquisa de marketing original, convertido de uma aplicação desktop Tkinter para uma aplicação web Flask.

## Funcionalidades

- **Autenticação**: Login e cadastro de usuários
- **Registro de Clientes**: Cadastro de novos clientes com informações detalhadas
- **Visualização**: Lista de clientes com busca e edição/exclusão
- **Relatórios**: Relatório geral e gráfico por origem
- **Export**: Exportar dados para Excel

## Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS (Bootstrap), JavaScript (Chart.js)
- **Banco de Dados**: SQLite
- **Bibliotecas**: pandas, openpyxl

## Como Executar

1. **Instalar dependências**:
   ```
   pip install -r requirements.txt
   ```

2. **Executar a aplicação**:
   ```
   python app.py
   ```

3. **Acessar o site**:
   Abra o navegador em `http://localhost:5000`

## Estrutura do Projeto

```
site_pesquisa_marketing/
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências Python
├── clientes.db           # Banco de dados SQLite
├── templates/            # Templates HTML
│   ├── base.html
│   ├── login.html
│   ├── cadastro_usuario.html
│   ├── dashboard.html
│   ├── registro.html
│   ├── visualizacao.html
│   ├── editar.html
│   ├── relatorios.html
│   ├── relatorio_geral.html
│   └── grafico_origem.html
└── static/               # Arquivos estáticos (CSS, JS, imagens)
```

## Responsividade

O site é totalmente responsivo, utilizando Bootstrap para garantir uma boa experiência em dispositivos móveis, tablets e desktops.

## Migração de Dados

O banco de dados `clientes.db` pode ser copiado do projeto original para manter os dados existentes.