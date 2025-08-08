document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('parameterModal');
    const closeBtn = modal.querySelector('.close');
    const cancelBtn = document.getElementById('cancelParam');
    const form = document.getElementById('parameterForm');
    const especeSelect = document.getElementById('espece');
    const timecloseGroup = document.getElementById('timecloseGroup');

    // Gestion de l'affichage du champ timetoclose
    especeSelect.addEventListener('change', (e) => {
        timecloseGroup.style.display = e.target.value === 'option5' ? 'block' : 'none';
    });

    // Charger les paramètres actuels
    async function loadCurrentParameters() {
        try {
            const response = await fetch('/parameter', {
                headers: {
                    'X-API-KEY': API_CONFIG.headers['X-API-KEY']
                }
            });
            const data = await response.json();
            
            document.getElementById('temperature').value = data.temperature;
            document.getElementById('humidity').value = data.humidity;
            document.getElementById('startDate').value = data.start_date.replace(' ', 'T');
            document.getElementById('statStepper').value = data.stat_stepper.toString();
            document.getElementById('numberStepper').value = data.number_stepper;
            document.getElementById('espece').value = Object.keys(especeMapping).find(key => 
                especeMapping[key] === data.espece
            ) || 'option5';
            
            if (data.espece === 'other') {
                document.getElementById('timetoclose').value = data.timetoclose;
                timecloseGroup.style.display = 'block';
            }
        } catch (error) {
            showError('Erreur lors du chargement des paramètres');
        }
    }

    // Soumission du formulaire
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = {
            temperature: parseFloat(document.getElementById('temperature').value),
            humidity: parseFloat(document.getElementById('humidity').value),
            start_date: document.getElementById('startDate').value,
            stat_stepper: document.getElementById('statStepper').value === 'true',
            number_stepper: parseInt(document.getElementById('numberStepper').value),
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
                modal.style.display = 'none';
                showSuccess('Paramètres mis à jour avec succès');
            } else {
                const error = await response.json();
                throw new Error(error.detail);
            }
        } catch (error) {
            showError(error.message);
        }
    });

    // Fermeture de la modal
    [closeBtn, cancelBtn].forEach(btn => {
        btn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    });

    // Fermeture en cliquant en dehors
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
});