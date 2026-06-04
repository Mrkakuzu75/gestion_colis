import sqlite3
import os
import math

DATABASE = 'colis.db'
TAUX_CONVERSION = 655.96
PRIX_PAR_KG = 10

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def arrondi_superieur(poids):
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
            destinataire_nom TEXT NOT NULL,
            destinataire_telephone TEXT NOT NULL,
            recuperateur_nom TEXT,
            recuperateur_telephone TEXT,
            type_colis TEXT NOT NULL,
            type_colis_autre TEXT,
            nombre_colis INTEGER DEFAULT 1,
            poids REAL,
            poids_arrondi REAL,
            prix_calcule REAL,
            prix_negocie REAL,
            prix_final REAL,
            montant_paye REAL,
            moyen_payement TEXT,
            payement_chez TEXT,
            est_negocie INTEGER DEFAULT 0,
            est_livreur INTEGER DEFAULT 0,
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
    print("Base de données créée avec succès!")

def calculer_prix(poids):
    if not poids or poids <= 0:
        return 0, 0, 0
    poids_arrondi = arrondi_superieur(poids)
    euros = poids_arrondi * PRIX_PAR_KG
    cfa = euros * TAUX_CONVERSION
    return round(euros, 2), round(cfa, 2), poids_arrondi

def get_prochains_statuts(statut_actuel):
    statuts = ['En attente', 'Validé', 'Parti', 'Arrivé', 'Récupéré']
    try:
        index = statuts.index(statut_actuel)
        if index < len(statuts) - 1:
            return statuts[index + 1:]
        return []
    except ValueError:
        return []