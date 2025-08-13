document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('parameterForm');
    if (!form) {
        alert('Formulaire non trouvé !');
        return;
    }
    const especeSelect = document.getElementById('espece');
    const timecloseGroup = document.getElementById('timecloseGroup');
    const timetocloseInput = document.getElementById('timetoclose');
    const API_CONFIG = {
        headers: {
            'X-API-KEY': 'votre_cle_api_1' // Mets ici ta vraie clé API
        }
    };

    // Affichage du champ timetoclose selon l'espèce
    especeSelect.addEventListener('change', (e) => {
        if (e.target.value === 'option5') {
            timecloseGroup.style.display = '';
            timetocloseInput.required = true;
        } else {
            timecloseGroup.style.display = 'none';
            timetocloseInput.required = false;
            timetocloseInput.value = '';
        }
    });

    // Charger les paramètres actuels depuis l'API
    async function loadCurrentParameters() {
        try {
            const response = await fetch('/api/parameter', {
                headers: {
                    'X-API-KEY': API_CONFIG.headers['X-API-KEY']
                }
            });
            if (!response.ok) throw new Error('Erreur API');
            const data = await response.json();

            document.getElementById('temperature').value = data.temperature;
            document.getElementById('humidity').value = data.humidity;
            if (data.start_date) {
                document.getElementById('start_date').value = data.start_date.replace(' ', 'T').slice(0, 16);
            }
            document.getElementById('stat_stepper').value = data.stat_stepper ? 'true' : 'false';
            document.getElementById('number_stepper').value = data.number_stepper;
            document.getElementById('espece').value = data.espece;

            if (data.espece === 'option5') {
                timetocloseInput.value = data.timetoclose || '';
                timecloseGroup.style.display = '';
                timetocloseInput.required = true;
            } else {
                timecloseGroup.style.display = 'none';
                timetocloseInput.required = false;
                timetocloseInput.value = '';
            }
        } catch (error) {
            alert('Erreur lors du chargement des paramètres');
            console.error(error);
        }
    }

    // Soumission du formulaire
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = {
            temperature: parseFloat(document.getElementById('temperature').value),
            humidity: parseFloat(document.getElementById('humidity').value),
            start_date: document.getElementById('start_date').value,
            stat_stepper: document.getElementById('stat_stepper').value === 'true',
            number_stepper: parseInt(document.getElementById('number_stepper').value),
            espece: document.getElementById('espece').value,
            timetoclose: document.getElementById('espece').value === 'option5' ? 
                parseInt(document.getElementById('timetoclose').value) : null
        };

        try {
            const response = await fetch('/parameter', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': API_CONFIG.headers['X-API-KEY']
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                alert('Paramètres mis à jour avec succès');
            } else {
                const error = await response.json();
                alert('Erreur : ' + error.detail);
            }
        } catch (error) {
            alert('Erreur lors de la soumission du formulaire');
            console.error(error);
        }
    });

    // Charger les valeurs au chargement de la page
    loadCurrentParameters();
});

