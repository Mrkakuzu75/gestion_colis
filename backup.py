import sqlite3
import os
import shutil
from datetime import datetime

DATABASE = 'colis.db'
BACKUP_DIR = 'backups'

def sauvegarder_base():
    """Sauvegarde la base de données dans le dossier backups"""
    if not os.path.exists(DATABASE):
        print("Aucune base à sauvegarder")
        return None
    
    # Créer le dossier backups si inexistant
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Dossier {BACKUP_DIR} créé")
    
    # Nom du fichier de sauvegarde avec date et heure
    date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_file = os.path.join(BACKUP_DIR, f'colis_backup_{date_str}.db')
    
    # Copier la base
    shutil.copy2(DATABASE, backup_file)
    print(f"✅ Sauvegarde créée: {backup_file}")
    
    # Supprimer les sauvegardes de plus de 30 jours
    supprimer_anciennes_sauvegardes()
    
    return backup_file

def supprimer_anciennes_sauvegardes(jours=30):
    """Supprime les sauvegardes plus vieilles que X jours"""
    if not os.path.exists(BACKUP_DIR):
        return
    
    maintenant = datetime.now()
    compteur = 0
    for fichier in os.listdir(BACKUP_DIR):
        chemin = os.path.join(BACKUP_DIR, fichier)
        if os.path.isfile(chemin) and fichier.startswith('colis_backup_') and fichier.endswith('.db'):
            modif = datetime.fromtimestamp(os.path.getmtime(chemin))
            if (maintenant - modif).days > jours:
                os.remove(chemin)
                compteur += 1
    
    if compteur > 0:
        print(f"🗑️ {compteur} ancienne(s) sauvegarde(s) supprimée(s)")

def lister_sauvegardes():
    """Retourne la liste des sauvegardes disponibles"""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    for fichier in os.listdir(BACKUP_DIR):
        if fichier.startswith('colis_backup_') and fichier.endswith('.db'):
            chemin = os.path.join(BACKUP_DIR, fichier)
            taille = os.path.getsize(chemin)
            date_modif = datetime.fromtimestamp(os.path.getmtime(chemin))
            backups.append({
                'nom': fichier,
                'chemin': chemin,
                'taille': taille,
                'date': date_modif.strftime('%d/%m/%Y %H:%M:%S')
            })
    return sorted(backups, key=lambda x: x['date'], reverse=True)

def restaurer_sauvegarde(nom_fichier):
    """Restaure une sauvegarde"""
    chemin_backup = os.path.join(BACKUP_DIR, nom_fichier)
    if not os.path.exists(chemin_backup):
        print(f"❌ Fichier {nom_fichier} non trouvé")
        return False
    
    # Sauvegarder la base actuelle avant restauration
    sauvegarder_base()
    
    # Restaurer
    shutil.copy2(chemin_backup, DATABASE)
    print(f"✅ Base restaurée depuis {nom_fichier}")
    return True

if __name__ == '__main__':
    sauvegarder_base()