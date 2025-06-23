from flask import Flask, render_template, request, redirect, url_for, session, flash
from urllib.parse import urlparse, parse_qs
from flask_mysqldb import MySQL
from datetime import datetime, date, timedelta
import MySQLdb.cursors
import requests
import re

app = Flask(__name__)
# Configuración de la base de datos
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mhbd'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.secret_key = 'clave_secreta_123'

mysql = MySQL(app)

# Ruta de inicio (login)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and 'usuario' in request.form and 'clave' in request.form:
        usuario = request.form['usuario']
        clave = request.form['clave']
        print (clave)
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT nombre, esadmin FROM usuarios WHERE usuario = %s AND clave2 = %s', (usuario, clave))
        account = cursor.fetchone()
        
        if account:
            session['loggedin'] = True
            session['nombre'] = account['nombre']
            session['usuario'] = usuario
            session['esadmin'] = account['esadmin']
            
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('auth/login.html')

# Dashboard principal
#@app.route('/dashboard')
#def dashboard():
#    if 'loggedin' in session:
#        print("Aqui estoy")
#        return render_template('dashboard.html')
#W    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Obtener estadísticas
        cursor.execute("SELECT COUNT(*) as total FROM usuafondo")
        total_usuarios = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT COUNT(*) as activos 
            FROM prest_biblio 
            WHERE fec_devuel = '0000-00-00' OR fec_devuel > CURDATE()
        """)
        prestamos_activos = cursor.fetchone()['activos']
        
        cursor.execute("""
            SELECT COUNT(*) as vencidos 
            FROM prest_biblio 
            WHERE fec_devuel < CURDATE() AND fec_devuel != '0000-00-00'
        """)
        prestamos_vencidos = cursor.fetchone()['vencidos']
        
        cursor.execute("""
            SELECT COUNT(*) as disponibles 
            FROM libro 
            WHERE cod_libro NOT IN (
                SELECT cod_libro FROM prest_biblio 
                WHERE fec_devuel = '0000-00-00' OR fec_devuel > CURDATE()
            )
        """)
        libros_disponibles = cursor.fetchone()['disponibles']
        
        # Préstamos recientes
        #    JOIN usuafondo u ON p.cod_usuario = u.cod_usuario
        cursor.execute("""
            SELECT p.*, u.nombre as nombre_usuario, l.Titulo as titulo_libro 
            FROM prest_biblio p
            JOIN usuafondo u ON p.id = u.cod_usuario
            JOIN libro l ON p.cutter = l.cutter AND p.dewey = l.dewey
            ORDER BY p.creado DESC LIMIT 5
        """)
        prestamos_recientes = cursor.fetchall()
        
        return render_template('dashboard.html', 
                            total_usuarios=total_usuarios,
                            prestamos_activos=prestamos_activos,
                            prestamos_vencidos=prestamos_vencidos,
                            libros_disponibles=libros_disponibles,
                            prestamos_recientes=prestamos_recientes)
    return redirect(url_for('login'))

# ... (resto del código)
def obtener_parametros_url(url):
  try:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params
  except:
    return None

# CRUD para UsuAfondo (usuarios del servicio)
@app.route('/usuarios')
def list_usuarios():
    if 'usuario' not in session:
        return render_template('auth/login.html',error='Debes iniciar sesión.')
                
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#        cursor.execute('SELECT * FROM usuafondo')
        cursor.execute('''
        SELECT u.cod_usuario,u.nombre,u.ape1,u.telefono,m.munic,d.depto,d.division
            FROM usuafondo u
            inner join municipios d on d.iddepto = u.departamento and d.idmuni=1
            inner join municipios m on m.idmuni = u.municipio and m.iddepto=u.departamento
            order by cod_usuario;
        ''')
        usuarios = cursor.fetchall()
        return render_template('usuarios/list.html', usuarios=usuarios)
    return redirect(url_for('login'))

@app.route('/usuarios/add', methods=['GET', 'POST'])
def add_usuario():
    if 'loggedin' in session:
        if request.method == 'POST':
            nombre = request.form['nombre']
            ape1 = request.form['ape1']
            ape2 = request.form['ape2']
            documento = request.form['documento']
            telefono = request.form['telefono']
            direccion = request.form['direccion']
            
            cursor = mysql.connection.cursor()
            cursor.execute('''
                INSERT INTO usuafondo 
                (nombre, ape1, ape2, documento, telefono, Direccion, status, NivAcceso, creadopor)
                VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s)
            ''', (nombre, ape1, ape2, documento, telefono, direccion, session['usuario']))
            mysql.connection.commit()
            flash('Usuario agregado correctamente', 'success')
            return redirect(url_for('list_usuarios'))
        
        return render_template('usuarios/form.html')
    return redirect(url_for('login'))

# CRUD para Libros
@app.route('/libros')
def list_libros():
    if 'usuario' not in session:
         return redirect(url_for('login'))
    if 'loggedin' in session:
        search = request.args.get('search', '')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        f'%{search}%'

        if search:
            cadena = "SELECT cod_libro, substring(titulo,1,50) titulo ,autor,concat(dewey,' - ',cutter) as ubic "
            cadena += "FROM libro "
            cadena += "WHERE Titulo LIKE %s OR autor LIKE %s"
     #       f'%{cadena}%'

            cursor.execute(cadena,(f'%{search}%',f'%{search}%'))
            #    '''
            #    SELECT * FROM libro 
            #    WHERE Titulo LIKE %s OR autor LIKE %s
            #''', (f'%{search}%', f'%{search}%'))
            
        else:
            cadena = 'SELECT cod_libro, substring(titulo,1,50) titulo ,autor,concat(dewey," - ",cutter) as ubic '
            cadena += 'FROM libro '
            cursor.execute(cadena)
            
        libros = cursor.fetchall()
        return render_template('libros/list.html', libros=libros, search=search)
    return redirect(url_for('login'))

# CRUD para Préstamos
@app.route('/prestamos')
def list_prestamos():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
                       
            SELECT p.cutter,p.dewey, u.nombre,u.ape1, l.Titulo as titulo_libro,p.fec_devuel,u.cod_usuario
            FROM prest_biblio p
            LEFT JOIN usuafondo u ON p.cod_afiliado = u.cod_usuario
            LEFT JOIN libro l ON p.cutter = l.cutter AND p.dewey = l.dewey
            WHERE p.status = 1 order by p.id           
        ''')
        prestamos = cursor.fetchall()
        return render_template('prestamos/list.html', prestamos=prestamos)
    return redirect(url_for('login'))

def add_days(n, d = datetime.today()):
  return d + timedelta(n)

#retorna las 
@app.route('/prestamos/upd/<cod_usuario>/<dewey>', methods=['GET', 'POST'])
def get_prestamo(cod_usuario,dewey):
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
                    SELECT p.id,p.usuario,p.fec_entrega,p.dewey,p.cutter,l.titulo,p.creadopor 
                    FROM prest_biblio p
                    inner join libro l on p.dewey=l.dewey and p.cutter = l.cutter
                    where p.cod_afiliado= %s and p.dewey= %s
                    ''',(cod_usuario,dewey))
        rs = cursor.fetchall()
        return render_template('prestamos/form_upd.html', data=rs)
    
@app.route('/end_prestamo', methods=['POST'])
def end_prestamo():
    if 'loggedin' in session:
        #if request.method == 'POST':
        id = request.form["aborrar"]
         # Acceder a datos del prestamo
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('update prest_biblio set status = 0 WHERE id = %s', (id,))
        mysql.connection.commit()
        cursor.close()
        flash('Préstamo procesado correctamente', 'success')
        return redirect(url_for('list_prestamos'))
        
         
@app.route('/prestamos/add', methods=['GET', 'POST'])
def add_prestamo():
    if 'loggedin' in session:
        if request.method == 'POST':
            cod_usuario = request.form['cod_usuario']
            cod_libro = request.form['cod_libro']
            fecha_entrega = datetime.now().strftime('%Y-%m-%d')
            
            # Obtener datos del libro
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM libro WHERE cod_libro = %s', (cod_libro,))
            libro = cursor.fetchone()
            
            # Obtener datos del libro
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT CONCAT(nombre," ",ape1," ",ape2) as nombre FROM usuafondo where cod_usuario = %s', (cod_usuario,))
            lector = cursor.fetchone()

            fecha_devuel = "0000-00-00"

            # Insertar préstamo
            cursor.execute('INSERT INTO prest_biblio (cod_afiliado, usuario, creadopor, fec_entrega, cutter, dewey,  fechaPrestamo, horaPrestamo,fec_devuel,cantidad,status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1,1)', (
                cod_usuario, 
                lector['nombre'],
                session['usuario'],
                fecha_entrega,
                libro['cutter'],
                libro['dewey'],
               # libro['lcc'],
               # session['usuario'],
                datetime.now().strftime('%Y-%m-%d'),
                datetime.now().strftime('%H:%M:%S'),
                fecha_devuel
            ))
            mysql.connection.commit()
            flash('Préstamo registrado correctamente', 'success')
            return redirect(url_for('list_prestamos'))
        
        # Obtener usuarios y libros para los selects
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT cod_usuario, CONCAT(nombre, " ", ape1) as nombre_completo FROM usuafondo')
        usuarios = cursor.fetchall()
        
        cursor.execute('SELECT cod_libro, Titulo, autor FROM libro')
        libros = cursor.fetchall()
        
        return render_template('prestamos/form.html', usuarios=usuarios, libros=libros)
    return redirect(url_for('login'))

        

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('nombre', None)
    session.pop('usuario', None)
    #session.pop('esadmin', None)
            
    return redirect(url_for('login'))

    
if __name__ == '__main__':
    app.run(debug=True, port=5000)
