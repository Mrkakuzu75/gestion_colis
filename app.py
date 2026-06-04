from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import database as db
import backup as bk
from functools import wraps

app = Flask(__name__)
app.secret_key = 'colispro_secret_key_2024'
ADMIN_PASSWORD = 'admin123'

# Faire une sauvegarde au démarrage
bk.sauvegarder_base()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error='Mot de passe incorrect')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET', 'POST'])
def add_colis():
    if request.method == 'POST':
        try:
            type_flux = request.form['type_flux']
            deposant_nom = request.form['deposant_nom']
            deposant_telephone = request.form['deposant_telephone']
            destinataire_nom = request.form['destinataire_nom']
            destinataire_telephone = request.form['destinataire_telephone']
            type_colis = request.form['type_colis']
            nombre_colis = int(request.form.get('nombre_colis', 1))
            moyen_payement = request.form.get('moyen_payement')
            payement_chez = request.form.get('payement_chez') if moyen_payement in ['Wave', 'Orange Money'] else None
            notes = request.form.get('notes', '')
            est_negocie = 1 if request.form.get('est_negocie') == 'on' else 0
            
            types_sans_poids = ['Document', 'Perruque', 'Maillot']
            
            if type_colis in types_sans_poids:
                prix_final = float(request.form.get('prix_negocie', 0))
                prix_calcule = None
                poids = None
                poids_arrondi = None
                prix_negocie = prix_final
            else:
                poids = float(request.form.get('poids', 0))
                prix_calcule, _, poids_arrondi = db.calculer_prix(poids)
                if est_negocie == 1 and request.form.get('prix_negocie'):
                    prix_negocie = float(request.form.get('prix_negocie'))
                    prix_final = prix_negocie
                else:
                    prix_negocie = None
                    prix_final = prix_calcule
            
            conn = db.get_db()
            conn.execute('''
                INSERT INTO colis (
                    type_flux, deposant_nom, deposant_telephone, 
                    destinataire_nom, destinataire_telephone, 
                    type_colis, nombre_colis, poids, poids_arrondi,
                    prix_calcule, prix_negocie, prix_final, 
                    moyen_payement, payement_chez, est_negocie, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (type_flux, deposant_nom, deposant_telephone, 
                  destinataire_nom, destinataire_telephone, 
                  type_colis, nombre_colis, poids, poids_arrondi,
                  prix_calcule, prix_negocie, prix_final, 
                  moyen_payement, payement_chez, est_negocie, notes))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Colis ajouté avec succès'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    return render_template('add_colis.html')

@app.route('/list')
@login_required
def list_colis():
    return render_template('list_colis.html')

@app.route('/suivi')
def suivi():
    return render_template('suivi.html')

@app.route('/recu/<int:id>')
def recu(id):
    conn = db.get_db()
    colis = conn.execute('SELECT * FROM colis WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not colis:
        return "Colis non trouvé", 404
    return render_template('recu_pdf.html', colis=dict(colis))
@app.route('/api/colis')
@login_required
def api_get_colis():
    conn = db.get_db()
    colis = conn.execute('SELECT * FROM colis ORDER BY date_creation DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in colis])

@app.route('/api/colis/<int:id>', methods=['PUT'])
@login_required
def api_update_colis(id):
    data = request.json
    conn = db.get_db()
    
    if 'statut' in data:
        nouveau_statut = data['statut']
        now = datetime.now().isoformat()
        
        if nouveau_statut == 'Validé':
            conn.execute('UPDATE colis SET statut = ?, date_validation = ? WHERE id = ?', 
                        (nouveau_statut, now, id))
        elif nouveau_statut == 'Parti':
            conn.execute('UPDATE colis SET statut = ?, date_expedition = ? WHERE id = ?',
                        (nouveau_statut, now, id))
        elif nouveau_statut in ['Arrivé', 'Récupéré']:
            conn.execute('UPDATE colis SET statut = ?, date_reception = ? WHERE id = ?',
                        (nouveau_statut, now, id))
        else:
            conn.execute('UPDATE colis SET statut = ? WHERE id = ?', (nouveau_statut, id))
        
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})

@app.route('/api/colis/<int:id>', methods=['DELETE'])
@login_required
def api_delete_colis(id):
    conn = db.get_db()
    conn.execute('DELETE FROM colis WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/stats')
@login_required
def api_get_stats():
    conn = db.get_db()
    total = conn.execute('SELECT COUNT(*) as count FROM colis').fetchone()['count']
    encaisse = conn.execute('SELECT SUM(prix_final) as total FROM colis WHERE statut = "Récupéré"').fetchone()['total'] or 0
    en_attente = conn.execute('SELECT COUNT(*) as count FROM colis WHERE statut = "En attente"').fetchone()['count']
    ce_mois = conn.execute('''SELECT COUNT(*) as count FROM colis 
                              WHERE strftime("%Y-%m", date_creation) = strftime("%Y-%m", "now")''').fetchone()['count']
    conn.close()
    return jsonify({
        'total': total,
        'encaisse': round(encaisse, 2),
        'en_attente': en_attente,
        'ce_mois': ce_mois
    })

@app.route('/api/recherche')
def api_recherche():
    terme = request.args.get('q', '').lower()
    if not terme or len(terme) < 2:
        return jsonify([])
    
    conn = db.get_db()
    results = conn.execute('''
        SELECT * FROM colis WHERE 
        LOWER(destinataire_telephone) LIKE ? OR 
        LOWER(deposant_nom) LIKE ? OR
        LOWER(destinataire_nom) LIKE ?
        ORDER BY date_creation DESC
    ''', (f'%{terme}%', f'%{terme}%', f'%{terme}%')).fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route('/api/statuts-possibles/<statut_actuel>')
def api_statuts_possibles(statut_actuel):
    return jsonify(db.get_prochains_statuts(statut_actuel))

if __name__ == '__main__':
    db.init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)