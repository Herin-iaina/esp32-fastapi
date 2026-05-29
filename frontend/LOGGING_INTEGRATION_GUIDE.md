# 🔧 Guide d'Intégration du Logger dans les Composants

Ce guide montre comment ajouter du logging aux composants React existants.

## Option 1: Utiliser le Hook `useLogger` (Recommandé)

### Étape 1: Importer le hook
```typescript
import { useLogger } from '../hooks/useLogger'
```

### Étape 2: Utiliser le hook dans le composant
```typescript
function MonComposant() {
  const { logButtonClick, logInfo, logError } = useLogger('MonComposant')

  const handleClick = () => {
    logButtonClick('Mon Bouton', { details: 'optionnelles' })
  }

  return <button onClick={handleClick}>Cliquer</button>
}
```

### Avantages
✅ Type-safe (TypeScript)  
✅ Composant automatiquement nommé  
✅ Méthodes optimisées avec `useCallback`  

---

## Option 2: Utiliser Directement le Logger

### Étape 1: Importer le logger
```typescript
import { logger } from '../utils/logger'
```

### Étape 2: Utiliser dans le composant
```typescript
function MonComposant() {
  const handleClick = () => {
    logger.logButtonClick('Mon Bouton', 'MonComposant', { id: 123 })
  }

  return <button onClick={handleClick}>Cliquer</button>
}
```

### Avantages
✅ Direct et simple  
✅ Accès à toutes les méthodes  
✅ Pas besoin de hook  

---

## Cas d'Utilisation Courants

### 1. Logger un Clic de Bouton

```typescript
const handleClick = () => {
  logger.logButtonClick('Ajouter Produit', 'Catalog', { productId: 123 })
}
```

### 2. Logger une Soumission de Formulaire

```typescript
const handleSubmit = async (formData) => {
  logger.logFormSubmit('Formulaire d\'inscription', 'RegisterPage', formData)
  
  try {
    const response = await fetch('/api/register', {
      method: 'POST',
      body: JSON.stringify(formData)
    })
    // ...
  } catch (err) {
    logger.logError('RegisterPage', 'Erreur lors de l\'inscription', err)
  }
}
```

### 3. Logger un Appel API

```typescript
const fetchData = async () => {
  logger.logAPICall('GET', '/api/users', 'pending')
  
  try {
    const response = await fetch('/api/users')
    if (response.ok) {
      logger.logAPICall('GET', '/api/users', 'success')
    } else {
      logger.logAPICall('GET', '/api/users', 'error')
    }
  } catch (err) {
    logger.logError('DataFetch', 'Erreur API', err)
  }
}
```

### 4. Logger les États de Chargement

```typescript
useEffect(() => {
  logger.logInfo('MyComponent', 'Composant monté')
  
  return () => {
    logger.logInfo('MyComponent', 'Composant démonté')
  }
}, [])
```

### 5. Logger les Changements d'État

```typescript
const [count, setCount] = useState(0)

const handleIncrement = () => {
  const newCount = count + 1
  setCount(newCount)
  logger.logInfo('Counter', 'Compteur incrémenté', { oldValue: count, newValue: newCount })
}
```

### 6. Logger les Validations

```typescript
const validateEmail = (email) => {
  const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  
  if (!isValid) {
    logger.logWarn('FormValidator', 'Email invalide', { email })
  } else {
    logger.logDebug('FormValidator', 'Email validé')
  }
  
  return isValid
}
```

---

## Exemple Complet: Composant Produit

```typescript
import { useState } from 'react'
import { logger } from '../utils/logger'

interface Product {
  id: number
  name: string
  price: number
}

function ProductCard({ product }: { product: Product }) {
  const [quantity, setQuantity] = useState(1)

  const handleAddToCart = async () => {
    logger.logButtonClick('Ajouter au Panier', 'ProductCard', { productId: product.id })
    
    try {
      logger.logAPICall('POST', `/api/cart/add/${product.id}`, 'pending')
      
      const response = await fetch(`/api/cart/add/${product.id}`, {
        method: 'POST',
        body: JSON.stringify({ quantity })
      })

      if (response.ok) {
        logger.logInfo('ProductCard', 'Produit ajouté au panier', { 
          productId: product.id, 
          quantity 
        })
        logger.logAPICall('POST', `/api/cart/add/${product.id}`, 'success')
      } else {
        logger.logWarn('ProductCard', 'Erreur lors de l\'ajout au panier')
        logger.logAPICall('POST', `/api/cart/add/${product.id}`, 'error')
      }
    } catch (err) {
      logger.logError('ProductCard', 'Erreur lors de l\'ajout au panier', err)
    }
  }

  return (
    <div className="product-card">
      <h3>{product.name}</h3>
      <p>${product.price}</p>
      <input 
        type="number" 
        value={quantity}
        onChange={(e) => {
          const newQuantity = parseInt(e.target.value)
          setQuantity(newQuantity)
          logger.logDebug('ProductCard', 'Quantité modifiée', { newQuantity })
        }}
      />
      <button onClick={handleAddToCart}>Ajouter au Panier</button>
    </div>
  )
}

export default ProductCard
```

---

## Méthodes du Logger

### `logButtonClick(buttonName, component, details?)`
Logger un clic de bouton
```typescript
logger.logButtonClick('Valider', 'Form', { formId: 'login' })
```

### `logFormSubmit(formName, component, data?)`
Logger une soumission de formulaire
```typescript
logger.logFormSubmit('Login Form', 'LoginPage', { username: 'john' })
```

### `logAPICall(method, endpoint, status?)`
Logger un appel API
```typescript
logger.logAPICall('POST', '/api/users', 'success')
```

### `logError(component, message, error?)`
Logger une erreur
```typescript
logger.logError('UserService', 'Erreur lors de la récupération des utilisateurs', err)
```

### `logInfo(component, message, details?)`
Logger une information
```typescript
logger.logInfo('Dashboard', 'Données chargées', { count: 42 })
```

### `logWarn(component, message, details?)`
Logger un avertissement
```typescript
logger.logWarn('Auth', 'Tentative de connexion échouée', { attempts: 3 })
```

### `logDebug(component, message, details?)`
Logger de débogage (pour développement)
```typescript
logger.logDebug('Store', 'État mis à jour', { store: appState })
```

---

## Bonnes Pratiques

✅ **Nommez clairement vos boutons**
```typescript
// Bon
logButtonClick('Créer Utilisateur', 'UserForm')

// Mauvais
logButtonClick('btn', 'Form')
```

✅ **Incluez les données pertinentes**
```typescript
// Bon
logButtonClick('Supprimer', 'UserList', { userId: 123 })

// Mauvais
logButtonClick('Supprimer', 'UserList')
```

✅ **Utilisez le niveau approprié**
```typescript
logger.logInfo('...') // Événements normaux
logger.logWarn('...') // Quelque chose d'inattendu mais pas d'erreur
logger.logError('...') // Erreur qui doit être corrigée
logger.logDebug('...') // Détails pour le débogage
```

✅ **Nettoyez les logs importants**
```typescript
// Au lieu de
logger.logDebug('Component', 'Données de la réponse entière', responseData)

// Préférez
logger.logDebug('Component', 'Réponse reçue', { status: response.status, count: data.length })
```

---

## Intégration Pas à Pas

### Pour un Composant Existant

1. **Importer le logger**
   ```typescript
   import { logger } from '../utils/logger'
   ```

2. **Ajouter les logs aux handlers**
   ```typescript
   const handleClick = () => {
     logger.logButtonClick('Mon Bouton', 'MyComponent')
     // ... code existant
   }
   ```

3. **Tester en console**
   ```javascript
   window.logger.printSummary()
   ```

---

## Dépannage

### Les logs n'apparaissent pas?

1. Vérifiez l'import:
   ```typescript
   import { logger } from '../utils/logger'
   ```

2. Vérifiez la console (F12 → Console)

3. Vérifiez que le composant est rendu:
   ```typescript
   logger.logInfo('MyComponent', 'Composant monté')
   ```

### Les logs disparaissent?

Les logs sont limités à 500 entrées. Les plus anciens sont supprimés:
```typescript
// Exporter avant qu'ils ne disparaissent
const logsJSON = window.logger.exportLogs()
copy(logsJSON)
```

---

## Ressources

- [Logger API Documentation](./frontend/src/utils/logger.ts)
- [useLogger Hook Documentation](./frontend/src/hooks/useLogger.ts)
- [DebugPanel Component](./frontend/src/components/DebugPanel.tsx)
- [Logging Debug Guide](./LOGGING_DEBUG_GUIDE.md)

---

Besoin de plus? Consultez le fichier [LOGGING_DEBUG_GUIDE.md](./LOGGING_DEBUG_GUIDE.md) pour des exemples avancés! 🚀
