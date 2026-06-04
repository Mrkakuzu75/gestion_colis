// Fonction d'export Excel
function exportToExcel() {
    fetch('/api/colis')
        .then(response => response.json())
        .then(colis => {
            if (colis.length === 0) {
                alert('Aucun colis à exporter');
                return;
            }
            
            // Créer le contenu CSV
            let csv = "ID;Date;Type Flux;Déposant;Tél Déposant;Destinataire;Tél Destinataire;Type Colis;Nb Colis;Poids(kg);Prix(€);Moyen Payement;Statut;Notes\n";
            
            colis.forEach(c => {
                csv += `${c.id};`;
                csv += `${new Date(c.date_creation).toLocaleDateString('fr-FR')};`;
                csv += `${c.type_flux === 'envoi_france' ? 'Envoi France' : 'Réception France'};`;
                csv += `${c.deposant_nom};`;
                csv += `${c.deposant_telephone};`;
                csv += `${c.destinataire_nom};`;
                csv += `${c.destinataire_telephone};`;
                csv += `${c.type_colis};`;
                csv += `${c.nombre_colis || 1};`;
                csv += `${c.poids || ''};`;
                csv += `${c.prix_final};`;
                csv += `${c.moyen_payement}${c.payement_chez ? ' ('+c.payement_chez+')' : ''};`;
                csv += `${c.statut};`;
                csv += `${c.notes || ''}\n`;
            });
            
            // Télécharger le fichier
            const blob = new Blob(["\uFEFF" + csv], {type: 'text/csv;charset=utf-8;'});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.href = url;
            link.setAttribute('download', `colis_export_${new Date().toISOString().slice(0,10)}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de l\'export');
        });
}

// Fonction pour imprimer le reçu
function imprimerRecu(id) {
    window.open(`/recu/${id}`, '_blank');
}