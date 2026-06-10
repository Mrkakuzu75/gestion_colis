from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from datetime import datetime
import sqlite3
import os
import math
from functools import wraps

app = Flask(__name__)
app.secret_key = 'colispro_secret_key_2024'
ADMIN_PASSWORD = 'admin123'
DATABASE = 'colis.db'
TAUX_CONVERSION = 655.96
PRIX_PAR_KG = 10

def generer_numero_suivi():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM colis").fetchone()[0]
    conn.close()

    date_str = datetime.now().strftime("%Y%m%d")
    return f"CE-{date_str}-{str(total + 1).zfill(4)}"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def arrondi_superieur(poids):
    if poids <= 0:
        return 0
    return math.ceil(poids)

def init_db():
    if os.path.exists(DATABASE):
        return
    conn = get_db()
    conn.execute('''
        CREATE TABLE colis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_flux TEXT NOT NULL,
            deposant_nom TEXT,
            deposant_telephone TEXT,
            livreur_nom TEXT,
            livreur_telephone TEXT,
            destinataire_nom TEXT,
            destinataire_telephone TEXT,
            recuperateur_nom TEXT,
            recuperateur_telephone TEXT,
            type_colis TEXT,
            type_colis_autre TEXT,
            nombre_colis INTEGER DEFAULT 1,
            poids REAL,
            poids_arrondi REAL,
            prix_final REAL,
            montant_paye REAL,
            moyen_payement TEXT,
            payement_chez TEXT,
            est_livreur INTEGER DEFAULT 0,
            est_negocie INTEGER DEFAULT 0,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_validation TIMESTAMP,
            date_expedition TIMESTAMP,
            date_reception TIMESTAMP,
            date_recuperation TIMESTAMP,
            statut TEXT DEFAULT 'En attente',
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Base de données prête")

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

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

@app.route('/add', methods=['POST'])
def add_colis_post():
    try:
        print("=== DONNÉES REÇUES ===")
        print(dict(request.form))
        
        type_flux = request.form.get('type_flux')
        est_livreur = request.form.get('est_livreur') == 'on'
        
        # ===== RÉCEPTION (France → Côte d'Ivoire) =====
        if type_flux == 'reception_france':
            destinataire_nom = request.form.get('destinataire_nom', '')
            destinataire_telephone = request.form.get('destinataire_telephone', '')
            type_colis = request.form.get('type_colis', '')
            type_colis_autre = request.form.get('type_colis_autre') if type_colis == 'Autre' else None
            montant_paye = float(request.form.get('montant_paye', 0))
            recuperateur_nom = request.form.get('recuperateur_nom', '')
            notes = request.form.get('notes', '')
            
            conn = get_db()
            conn.execute('''
                INSERT INTO colis (type_flux, destinataire_nom, destinataire_telephone,
                type_colis, type_colis_autre, prix_final, montant_paye,
                recuperateur_nom, notes, statut)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('reception_france', destinataire_nom, destinataire_telephone,
                  type_colis, type_colis_autre, montant_paye, montant_paye,
                  recuperateur_nom, notes, 'En attente'))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Colis réception enregistré'})
        
        # ===== ENVOI (Côte d'Ivoire → France) =====
        else:
            if est_livreur:
                # MODE TRANSPORTEUR (LIVREUR)
                print("=== MODE TRANSPORTEUR ===")
                destinataire_nom = request.form.get('destinataire_nom', '')
                destinataire_telephone = request.form.get('destinataire_telephone', '')
                type_colis = request.form.get('type_colis', '')
                type_colis_autre = request.form.get('type_colis_autre') if type_colis == 'Autre' else None
                poids = float(request.form.get('poids', 0))
                est_negocie = request.form.get('est_negocie') == 'on'
                
                if est_negocie:
                    prix_final = float(request.form.get('prix_negocie', 0))
                else:
                    poids_arrondi = arrondi_superieur(poids)
                    prix_final = poids_arrondi * PRIX_PAR_KG
                
                moyen_payement = request.form.get('moyen_payement', '')
                payement_chez = request.form.get('payement_chez') if moyen_payement in ['Wave', 'Orange Money'] else None
                notes = request.form.get('notes', '')
                
                conn = get_db()
                conn.execute('''
                    INSERT INTO colis (
                        type_flux, est_livreur, livreur_nom, livreur_telephone,
                        destinataire_nom, destinataire_telephone, type_colis, type_colis_autre,
                        poids, prix_final, montant_paye, moyen_payement, payement_chez, notes, statut
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('envoi_france', 1, 'Transporteur', '-', 
                      destinataire_nom, destinataire_telephone,
                      type_colis, type_colis_autre, poids, prix_final, prix_final,
                      moyen_payement, payement_chez, notes, 'En attente'))
                conn.commit()
                conn.close()
                return jsonify({'success': True, 'message': 'Colis transporteur ajouté'})
            
            else:
                # MODE DÉPOSANT
                print("=== MODE DÉPOSANT ===")
                deposant_nom = request.form.get('deposant_nom', '')
                deposant_telephone = request.form.get('deposant_telephone', '')
                destinataire_nom = request.form.get('destinataire_nom', '')
                destinataire_telephone = request.form.get('destinataire_telephone', '')
                type_colis = request.form.get('type_colis', '')
                type_colis_autre = request.form.get('type_colis_autre') if type_colis == 'Autre' else None
                nombre_colis = int(request.form.get('nombre_colis', 1))
                poids = float(request.form.get('poids', 0))
                moyen_payement = request.form.get('moyen_payement', '')
                payement_chez = request.form.get('payement_chez') if moyen_payement in ['Wave', 'Orange Money'] else None
                est_negocie = request.form.get('est_negocie') == 'on'
                notes = request.form.get('notes', '')
                
                types_sans_poids = ['Document', 'Perruque', 'Maillot']
                
                if type_colis in types_sans_poids:
                    if est_negocie:
                        prix_final = float(request.form.get('prix_negocie', 0))
                    else:
                        prix_final = 0
                    poids_arrondi = None
                else:
                    if est_negocie:
                        prix_final = float(request.form.get('prix_negocie', 0))
                    else:
                        poids_arrondi = arrondi_superieur(poids)
                        prix_final = poids_arrondi * PRIX_PAR_KG
                
                conn = get_db()
                conn.execute('''
                    INSERT INTO colis (type_flux, deposant_nom, deposant_telephone,
                    destinataire_nom, destinataire_telephone, type_colis, type_colis_autre,
                    nombre_colis, poids, poids_arrondi, prix_final, montant_paye, moyen_payement, payement_chez, est_negocie, notes, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('envoi_france', deposant_nom, deposant_telephone, destinataire_nom,
                      destinataire_telephone, type_colis, type_colis_autre, nombre_colis,
                      poids, poids_arrondi if 'poids_arrondi' in locals() else None, prix_final, prix_final,
                      moyen_payement, payement_chez, 1 if est_negocie else 0, notes, 'En attente'))
                conn.commit()
                conn.close()
                return jsonify({'success': True, 'message': 'Colis ajouté'})
                
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/add', methods=['GET'])
def add_colis_get():
    return render_template('add_colis.html')

@app.route('/list')
@login_required
def list_colis():
    return render_template('list_colis.html')

@app.route('/suivi')
def suivi():
    return render_template('suivi.html')

@app.route('/recuperation')
@login_required
def recuperation():
    return render_template('recuperation.html')

@app.route('/recu/<int:id>')
def recu(id):
    conn = get_db()
    colis = conn.execute('SELECT * FROM colis WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not colis:
        return "Colis non trouvé", 404
    return render_template('recu_pdf.html', colis=dict(colis))

@app.route('/api/colis')
@login_required
def api_get_colis():
    conn = get_db()
    colis = conn.execute('SELECT * FROM colis ORDER BY date_creation DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in colis])

@app.route('/api/colis/<int:id>')
@login_required
def api_get_colis_by_id(id):
    conn = get_db()
    colis = conn.execute('SELECT * FROM colis WHERE id = ?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(colis) if colis else {})

@app.route('/api/colis/<int:id>', methods=['PUT'])
@login_required
def api_update_colis(id):
    data = request.json
    conn = get_db()
    if 'statut' in data:
        now = datetime.now().isoformat()
        nouveau = data['statut']
        if nouveau == 'Validé':
            conn.execute('UPDATE colis SET statut=?, date_validation=? WHERE id=?', (nouveau, now, id))
        elif nouveau == 'Parti':
            conn.execute('UPDATE colis SET statut=?, date_expedition=? WHERE id=?', (nouveau, now, id))
        elif nouveau == 'Arrivé':
            conn.execute('UPDATE colis SET statut=?, date_reception=? WHERE id=?', (nouveau, now, id))
        elif nouveau == 'Récupéré':
            conn.execute('UPDATE colis SET statut=?, date_recuperation=? WHERE id=?', (nouveau, now, id))
        else:
            conn.execute('UPDATE colis SET statut=? WHERE id=?', (nouveau, id))
        conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/colis/<int:id>', methods=['DELETE'])
@login_required
def api_delete_colis(id):
    conn = get_db()
    conn.execute('DELETE FROM colis WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/colis/<int:id>/statut', methods=['POST'])
@login_required
def api_update_statut_complet(id):
    data = request.json
    nouveau_statut = data.get('statut')
    montant_paye = data.get('montant_paye')
    recuperateur_nom = data.get('recuperateur_nom')
    
    conn = get_db()
    now = datetime.now().isoformat()
    
    if nouveau_statut == 'Récupéré':
        conn.execute('''
            UPDATE colis 
            SET statut = ?, date_recuperation = ?, 
                montant_paye = ?, prix_final = ?, 
                recuperateur_nom = ?
            WHERE id = ?
        ''', (nouveau_statut, now, montant_paye, montant_paye, recuperateur_nom, id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/colis/arrivants/en-attente')
@login_required
def api_colis_arrivants_en_attente():
    conn = get_db()
    colis = conn.execute('''
        SELECT * FROM colis 
        WHERE (statut = 'En attente' OR statut IS NULL)
        ORDER BY date_creation DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in colis])

@app.route('/api/colis/arrivants/recherche')
@login_required
def api_colis_arrivants_recherche():
    terme = request.args.get('q', '').lower()
    terme_chiffres = ''.join(filter(str.isdigit, terme))
    
    conn = get_db()
    
    colis = conn.execute('''
        SELECT * FROM colis 
        WHERE (statut = 'En attente' OR statut IS NULL)
        AND (
            LOWER(destinataire_telephone) LIKE ? OR 
            LOWER(destinataire_nom) LIKE ? OR
            LOWER(recuperateur_telephone) LIKE ?
        )
        ORDER BY date_creation DESC
    ''', (f'%{terme}%', f'%{terme}%', f'%{terme}%')).fetchall()
    
    if len(colis) == 0 and terme_chiffres:
        colis = conn.execute('''
            SELECT * FROM colis 
            WHERE (statut = 'En attente' OR statut IS NULL)
            AND (
                REPLACE(REPLACE(REPLACE(destinataire_telephone, ' ', ''), '-', ''), '+', '') LIKE ? OR
                REPLACE(REPLACE(REPLACE(recuperateur_telephone, ' ', ''), '-', ''), '+', '') LIKE ?
            )
            ORDER BY date_creation DESC
        ''', (f'%{terme_chiffres}%', f'%{terme_chiffres}%')).fetchall()
    
    conn.close()
    return jsonify([dict(row) for row in colis])

@app.route('/api/recherche')
def api_recherche():
    terme = request.args.get('q', '').strip()
    if len(terme) < 2:
        return jsonify([])
    
    terme_chiffres = ''.join(filter(str.isdigit, terme))
    
    conn = get_db()
    colis_list = conn.execute('SELECT * FROM colis ORDER BY date_creation DESC').fetchall()
    
    results = []
    for colis in colis_list:
        c = dict(colis)
        tel_dest = ''.join(filter(str.isdigit, c.get('destinataire_telephone') or ''))
        tel_dep = ''.join(filter(str.isdigit, c.get('deposant_telephone') or ''))
        nom_dest = (c.get('destinataire_nom') or '').lower()
        nom_dep = (c.get('deposant_nom') or '').lower()
        
        match = False
        if terme_chiffres and (terme_chiffres in tel_dest or terme_chiffres in tel_dep):
            match = True
        elif len(terme) > 2 and (terme.lower() in nom_dest or terme.lower() in nom_dep):
            match = True
        
        if match:
            results.append(c)
    
    conn.close()
    return jsonify(results)

@app.route('/api/stats')
@login_required
def api_get_stats():
    mois = request.args.get('mois', 'current')
    
    conn = get_db()
    
    total = conn.execute('SELECT COUNT(*) as c FROM colis').fetchone()['c']
    en_attente = conn.execute('SELECT COUNT(*) as c FROM colis WHERE statut = "En attente"').fetchone()['c']
    
    if mois == 'current':
        encaisse = conn.execute('SELECT SUM(prix_final) as s FROM colis WHERE strftime("%Y-%m", date_creation) = strftime("%Y-%m", "now") AND prix_final > 0').fetchone()['s'] or 0
        ce_mois = conn.execute('SELECT COUNT(*) as c FROM colis WHERE strftime("%Y-%m", date_creation) = strftime("%Y-%m", "now")').fetchone()['c']
        nom_mois = datetime.now().strftime('%B %Y')
    else:
        encaisse = conn.execute('SELECT SUM(prix_final) as s FROM colis WHERE strftime("%Y-%m", date_creation) = ? AND prix_final > 0', (mois,)).fetchone()['s'] or 0
        ce_mois = conn.execute('SELECT COUNT(*) as c FROM colis WHERE strftime("%Y-%m", date_creation) = ?', (mois,)).fetchone()['c']
        date_obj = datetime.strptime(mois, '%Y-%m')
        nom_mois = date_obj.strftime('%B %Y')
    
    conn.close()
    
    return jsonify({
        'total': total,
        'encaisse': round(encaisse, 2),
        'en_attente': en_attente,
        'ce_mois': ce_mois,
        'nom_mois': nom_mois
    })

@app.route('/api/mois-disponibles')
@login_required
def api_mois_disponibles():
    conn = get_db()
    mois = conn.execute('''
        SELECT DISTINCT strftime("%Y-%m", date_creation) as mois 
        FROM colis 
        ORDER BY mois DESC
    ''').fetchall()
    conn.close()
    
    resultats = []
    for m in mois:
        if m['mois']:
            date_obj = datetime.strptime(m['mois'], '%Y-%m')
            resultats.append({
                'value': m['mois'],
                'label': date_obj.strftime('%B %Y')
            })
    
    return jsonify(resultats)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)