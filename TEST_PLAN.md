# Plan de Test - Système d'Incubation

## ✅ Tests à effectuer

### 1. Frontend - Authentification
- [ ] Accéder à http://localhost:8000/
- [ ] Cliquer sur "Paramètres"
- [ ] Voir le formulaire de connexion
- [ ] Entrer username: **admin**, password: **test123456**
- [ ] Cliquer sur "Se connecter"
- [ ] Vérifier que l'utilisateur est connecté

### 2. Frontend - Mode Sombre
- [ ] Cliquer sur le bouton de toggle du mode sombre (Sun/Moon icon)
- [ ] Vérifier que les couleurs changent
- [ ] Rafraîchir la page et vérifier que le mode est conservé
- [ ] Retourner au mode clair

### 3. Frontend - Paramètres d'Incubation
Une fois connecté, remplir et tester:
- [ ] **Espèce**: Sélectionner "Poule" → doit afficher conseil "37.5°C"
- [ ] **Espèce**: Sélectionner "Canard" → doit afficher conseil "37.5°C"  
- [ ] **Jours jusqu'à l'éclosion**: Modifier à 21 (poule)
- [ ] **Rotations par jour**: Modifier à 5

### 4. Frontend - Contrôle de Température
- [ ] **Température cible**: Modifier à 37.5°C
- [ ] **Température actuelle**: Affichage en lecture seule (grisé)
- [ ] Vérifier que la zone affiche le conseil pour l'espèce sélectionnée

### 5. Frontend - Contrôle d'Humidité
- [ ] **Humidité cible**: Modifier à 65%
- [ ] **Humidité actuelle**: Affichage en lecture seule (grisé)
- [ ] Vérifier l'affichage du conseil "J1-J18: 40-50%, J19+: 70-75%"

### 6. Frontend - Configuration du Matériel
- [ ] **Moteur de rotation**: Cocher "Activer le moteur de rotation automatique"
- [ ] **Nombre de tourneurs**: Modifier à 2

### 7. Frontend - Date de Cycle
- [ ] **Date et heure de début**: Sélectionner une date/heure avec le picker

### 8. Frontend - Sauvegarde
- [ ] Cliquer sur "Sauvegarder"
- [ ] Vérifier le message de succès "Paramètres sauvegardés avec succès !"
- [ ] Le message doit disparaître après 3 secondes

### 9. Backend - Vérification en Base
Exécuter dans le terminal:
```bash
docker exec esp32-db psql -U user -d smartelia_db -c \
  "SELECT espece, temp_incubation, humidity_target, rotation_count, user_id FROM parameter_data ORDER BY id DESC LIMIT 1;"
```
Vérifier les valeurs sauvegardées

### 10. Frontend - Déconnexion
- [ ] Cliquer sur "Se Déconnecter"
- [ ] Vérifier le retour au formulaire de connexion

### 11. Frontend - Sauvegarder sans Authentification
- [ ] Rafraîchir la page (formulaire de login)
- [ ] Essayer de cliquer sur "Sauvegarder" (doit être désactivé ou afficher erreur)
- [ ] Se reconnecter et retenter

### 12. Dashboard - Affichage
- [ ] Cliquer sur "Tableau de Bord"
- [ ] Vérifier l'affichage des graphiques
- [ ] Vérifier que le mode sombre s'applique aussi au dashboard

### 13. Mode Sombre - Persistance
- [ ] Activer le mode sombre
- [ ] Rafraîchir la page
- [ ] Vérifier que le mode sombre est toujours actif

## Résumé API

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test123456"}'
```
Réponse: JWT token valide

### Récupérer Paramètres
```bash
curl http://localhost:8000/api/parameter
```

### Sauvegarder Paramètres
```bash
curl -X POST http://localhost:8000/api/parameter \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{...}'
```

## Critères de Succès

✅ Tous les tests doivent passer
✅ Pas d'erreurs dans la console du navigateur
✅ Les paramètres sont persistés en base de données
✅ Le mode sombre fonctionne et est persisté
✅ L'authentification est requise pour modifier les paramètres
✅ Les messages d'erreur/succès s'affichent correctement
