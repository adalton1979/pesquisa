from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import pandas as pd
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import io

app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessao'  # Mude isso em produção

# Conexão com o banco
def get_db():
    conn = sqlite3.connect('clientes.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar banco
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Tabela usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    ''')

    # Tabela clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            origem TEXT,
            regiao_origem TEXT,
            contrato TEXT,
            atendente TEXT,
            data_cadastro DATE,
            data_pesquisa DATE,
            observacoes TEXT
        )
    ''')

    # Tabela origens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS origens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Funções auxiliares
def corrigir_datas_antigas():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, data_pesquisa FROM clientes WHERE data_pesquisa IS NOT NULL AND data_pesquisa != ''")
    registros = cursor.fetchall()
    for reg in registros:
        id_cliente, data_pesquisa = reg['id'], reg['data_pesquisa']
        try:
            data_corrigida = datetime.strptime(data_pesquisa, "%d-%m-%Y").strftime("%Y-%m-%d")
            cursor.execute("UPDATE clientes SET data_pesquisa = ? WHERE id = ?", (data_corrigida, id_cliente))
        except ValueError:
            pass
    conn.commit()
    conn.close()

def corrigir_datas_pesquisa():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clientes
        SET data_pesquisa = data_cadastro
        WHERE data_pesquisa IS NULL OR data_pesquisa = '';
    """)
    conn.commit()
    conn.close()

def corrigir_origens():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clientes
        SET origem = TRIM(UPPER(origem)),
            regiao_origem = TRIM(UPPER(regiao_origem)),
            atendente = TRIM(UPPER(atendente))
        WHERE origem IS NOT NULL OR regiao_origem IS NOT NULL OR atendente IS NOT NULL;
    """)
    conn.commit()
    conn.close()

def lista_origens():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT origem FROM clientes WHERE origem IS NOT NULL AND TRIM(origem) <> ''")
    dados = cursor.fetchall()
    conn.close()
    origens = sorted({d['origem'].strip().upper() for d in dados if d['origem']})
    return origens

# Rotas
@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip().lower()
        senha = request.form['senha'].strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT nome, senha FROM usuarios WHERE LOWER(usuario)=?", (usuario,))
        resultado = cursor.fetchone()
        conn.close()
        if resultado:
            senha_armazenada = resultado['senha']
            # Verificar se a senha está hasheada (começa com scrypt) ou em texto plano
            if senha_armazenada.startswith('scrypt:'):
                # Senha hasheada
                if check_password_hash(senha_armazenada, senha):
                    session['usuario'] = resultado['nome']
                    flash('Login realizado com sucesso!', 'success')
                    return redirect(url_for('dashboard'))
            else:
                # Senha em texto plano (compatibilidade com usuários existentes)
                if senha_armazenada == senha:
                    session['usuario'] = resultado['nome']
                    flash('Login realizado com sucesso!', 'success')
                    return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos', 'error')
    return render_template('login.html')

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip().lower()
        senha = request.form['senha'].strip()
        confirmar_senha = request.form['confirmar_senha'].strip()

        if not usuario or not senha or not confirmar_senha:
            flash('Preencha todos os campos', 'error')
            return redirect(url_for('recuperar_senha'))

        if senha != confirmar_senha:
            flash('As senhas não coincidem', 'error')
            return redirect(url_for('recuperar_senha'))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(usuario)=?", (usuario,))
        resultado = cursor.fetchone()
        if not resultado:
            conn.close()
            flash('Usuário não encontrado', 'error')
            return redirect(url_for('recuperar_senha'))

        hashed_senha = generate_password_hash(senha)
        cursor.execute("UPDATE usuarios SET senha=? WHERE id=?", (hashed_senha, resultado['id']))
        conn.commit()
        conn.close()

        flash('Senha atualizada com sucesso! Faça login com a nova senha.', 'success')
        return redirect(url_for('login'))

    return render_template('recuperar_senha.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Logout realizado', 'info')
    return redirect(url_for('login'))

@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        usuario = request.form['usuario'].strip().lower()
        senha = request.form['senha'].strip()
        if not nome or not usuario or not senha:
            flash('Preencha todos os campos', 'error')
            return redirect(url_for('cadastro_usuario'))
        hashed_senha = generate_password_hash(senha)
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO usuarios (nome, usuario, senha) VALUES (?, ?, ?)", (nome, usuario, hashed_senha))
            conn.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Usuário já existe', 'error')
        finally:
            conn.close()
    return render_template('cadastro_usuario.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', usuario=session['usuario'])

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form['nome'].strip().upper()
        origem = request.form['origem'].strip().upper()
        regiao_origem = request.form['regiao_origem'].strip().upper()
        contrato = request.form['contrato'].strip().upper()
        data_pesquisa = request.form['data_pesquisa'].strip()
        observacoes = request.form['observacoes'].strip().upper()

        if not nome or not origem or not regiao_origem or not contrato or not data_pesquisa:
            flash('Preencha todos os campos obrigatórios', 'error')
            return redirect(url_for('registro'))

        try:
            data_pesquisa = datetime.strptime(data_pesquisa, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            flash('Data inválida', 'error')
            return redirect(url_for('registro'))

        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        atendente = session['usuario'].upper()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clientes (nome, origem, regiao_origem, contrato, atendente, data_cadastro, data_pesquisa, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome, origem, regiao_origem, contrato, atendente, data_cadastro, data_pesquisa, observacoes))
        conn.commit()
        conn.close()
        flash('Cliente registrado com sucesso!', 'success')
        return redirect(url_for('registro'))

    origens = lista_origens()
    return render_template('registro.html', origens=origens)

@app.route('/visualizacao')
def visualizacao():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nome, origem, regiao_origem, contrato, atendente,
               strftime('%d-%m-%Y', data_cadastro) AS data_cadastro,
               strftime('%d-%m-%Y', data_pesquisa) AS data_pesquisa,
               observacoes
        FROM clientes
        ORDER BY data_cadastro DESC
    """)
    clientes = cursor.fetchall()
    conn.close()
    return render_template('visualizacao.html', clientes=clientes)

@app.route('/buscar', methods=['POST'])
def buscar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    termo = request.form['termo'].strip().upper()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT id, nome, origem, regiao_origem, contrato, atendente,
               strftime('%d-%m-%Y', data_cadastro) AS data_cadastro,
               strftime('%d-%m-%Y', data_pesquisa) AS data_pesquisa,
               observacoes
        FROM clientes
        WHERE nome LIKE '%{termo}%' OR origem LIKE '%{termo}%' OR contrato LIKE '%{termo}%' OR atendente LIKE '%{termo}%'
        ORDER BY data_pesquisa DESC
    """)
    clientes = cursor.fetchall()
    conn.close()
    return render_template('visualizacao.html', clientes=clientes, termo=termo)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome'].strip().upper()
        origem = request.form['origem'].strip().upper()
        regiao_origem = request.form['regiao_origem'].strip().upper()
        contrato = request.form['contrato'].strip().upper()
        atendente = request.form['atendente'].strip().upper()
        data_cadastro = request.form['data_cadastro']
        data_pesquisa = request.form['data_pesquisa']
        observacoes = request.form['observacoes'].strip().upper()

        cursor.execute("""
            UPDATE clientes SET nome=?, origem=?, regiao_origem=?, contrato=?, atendente=?, data_cadastro=?, data_pesquisa=?, observacoes=?
            WHERE id=?
        """, (nome, origem, regiao_origem, contrato, atendente, data_cadastro, data_pesquisa, observacoes, id))
        conn.commit()
        flash('Cliente atualizado!', 'success')
        conn.close()
        return redirect(url_for('visualizacao'))

    cursor.execute("SELECT * FROM clientes WHERE id=?", (id,))
    cliente = cursor.fetchone()
    origens = lista_origens()
    conn.close()
    return render_template('editar.html', cliente=cliente, origens=origens)

@app.route('/excluir/<int:id>')
def excluir(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Cliente excluído!', 'success')
    return redirect(url_for('visualizacao'))

@app.route('/relatorios')
def relatorios():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('relatorios.html')

@app.route('/relatorio_geral')
def relatorio_geral():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT id, nome, origem, regiao_origem, contrato, atendente,
               strftime('%d-%m-%Y', data_cadastro) AS data_cadastro,
               strftime('%d-%m-%Y', data_pesquisa) AS data_pesquisa,
               observacoes
        FROM clientes
        ORDER BY data_cadastro DESC
    """, conn)
    conn.close()
    return render_template('relatorio_geral.html', clientes=df.to_dict('records'))

@app.route('/grafico_origem')
def grafico_origem():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("SELECT TRIM(UPPER(origem)) AS origem, COUNT(*) as total FROM clientes WHERE origem IS NOT NULL AND TRIM(origem) <> '' GROUP BY origem", conn)
    conn.close()
    labels = df['origem'].tolist()
    data = df['total'].tolist()
    return render_template('grafico_origem.html', labels=labels, data=data)

@app.route('/relatorio_mensal')
def relatorio_mensal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT strftime('%m/%Y', data_pesquisa) AS mes,
               COUNT(*) AS total
        FROM clientes
        WHERE data_pesquisa IS NOT NULL
        GROUP BY strftime('%Y-%m', data_pesquisa)
        ORDER BY strftime('%Y-%m', data_pesquisa) DESC
    """, conn)
    conn.close()
    return render_template('relatorio_mensal.html', dados=df.to_dict('records'))

@app.route('/relatorio_origem')
def relatorio_origem():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT TRIM(UPPER(origem)) AS origem, COUNT(*) AS total
        FROM clientes
        WHERE origem IS NOT NULL
          AND TRIM(origem) <> ''
        GROUP BY origem
        ORDER BY total DESC
    """, conn)
    conn.close()
    return render_template('relatorio_origem.html', dados=df.to_dict('records'))

@app.route('/relatorio_origem_mensal')
def relatorio_origem_mensal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT strftime('%Y-%m', data_pesquisa) AS mes,
               TRIM(UPPER(origem)) AS origem,
               COUNT(*) AS total
        FROM clientes
        WHERE origem IS NOT NULL
          AND TRIM(origem) != ''
          AND data_pesquisa IS NOT NULL
          AND data_pesquisa != ''
        GROUP BY mes, origem
        ORDER BY mes DESC, origem
    """, conn)
    conn.close()

    df['origem'] = df['origem'].astype(str).str.upper()
    if df.empty:
        return render_template('relatorio_origem_mensal.html', registros=[], origens=[], totais={}, total_geral=0)

    pivot = df.pivot(index='mes', columns='origem', values='total').fillna(0).astype(int)
    pivot = pivot.sort_index(ascending=False)
    registros = pivot.reset_index().to_dict('records')
    origens = list(pivot.columns)
    totais = pivot.sum().to_dict()
    total_geral = int(pivot.values.sum())
    return render_template('relatorio_origem_mensal.html', registros=registros, origens=origens, totais=totais, total_geral=total_geral)

@app.route('/relatorio_atendente')
def relatorio_atendente():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT TRIM(UPPER(atendente)) AS atendente, COUNT(*) AS total
        FROM clientes
        WHERE atendente IS NOT NULL
          AND TRIM(atendente) <> ''
        GROUP BY TRIM(UPPER(atendente))
        ORDER BY total DESC
    """, conn)
    conn.close()
    return render_template('relatorio_atendente.html', dados=df.to_dict('records'))

@app.route('/relatorio_progresso')
def relatorio_progresso():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT strftime('%Y-%m', data_pesquisa) AS mes,
               COUNT(*) AS total
        FROM clientes
        WHERE data_pesquisa IS NOT NULL
        GROUP BY strftime('%Y-%m', data_pesquisa)
        ORDER BY mes ASC
    """, conn)
    conn.close()
    
    # Calcular progresso acumulado
    df['progresso'] = df['total'].cumsum()
    labels = df['mes'].tolist()
    totais = df['total'].tolist()
    progresso = df['progresso'].tolist()
    
    return render_template('relatorio_progresso.html', labels=labels, totais=totais, progresso=progresso, dados=df.to_dict('records'))

@app.route('/exportar_excel')
def exportar_excel():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM clientes", conn)
    conn.close()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes')
    output.seek(0)
    return send_file(output, download_name='clientes.xlsx', as_attachment=True)

@app.route('/gerenciar_origens')
def gerenciar_origens():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM origens ORDER BY nome")
    origens = cursor.fetchall()
    conn.close()
    return render_template('gerenciar_origens.html', origens=origens)

@app.route('/adicionar_origem', methods=['POST'])
def adicionar_origem():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    nome_origem = request.form['nome_origem'].strip().upper()
    if not nome_origem:
        flash('Digite um nome para a origem', 'error')
        return redirect(url_for('gerenciar_origens'))
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO origens (nome) VALUES (?)", (nome_origem,))
        conn.commit()
        flash(f'Origem "{nome_origem}" adicionada com sucesso!', 'success')
    except sqlite3.IntegrityError:
        flash('Esta origem já existe', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('gerenciar_origens'))

@app.route('/excluir_origem/<int:id>')
def excluir_origem(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar se a origem está sendo usada por algum cliente
    cursor.execute("SELECT COUNT(*) as total FROM clientes WHERE origem = (SELECT nome FROM origens WHERE id = ?)", (id,))
    uso = cursor.fetchone()
    
    if uso['total'] > 0:
        flash(f'Não é possível excluir esta origem pois está sendo usada por {uso["total"]} cliente(s)', 'error')
    else:
        cursor.execute("DELETE FROM origens WHERE id = ?", (id,))
        conn.commit()
        flash('Origem excluída com sucesso!', 'success')
    
    conn.close()
    return redirect(url_for('gerenciar_origens'))

if __name__ == '__main__':
    init_db()
    corrigir_datas_antigas()
    corrigir_datas_pesquisa()
    corrigir_origens()
    app.run(debug=True)