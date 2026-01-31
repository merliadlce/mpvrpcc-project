# MPVRP-CC Solver avec OR-Tools

## 📋 Description

Solveur pour le problème Multi-Product Vehicle Routing Problem with Changeover Cost (MPVRP-CC) utilisant **Google OR-Tools** comme moteur d'optimisation.

### Caractéristiques principales

- ✅ **OR-Tools Integration** : Utilisation du routage solver de Google OR-Tools
- ✅ **Décomposition produit-par-produit** : Résolution efficace pour multi-produits
- ✅ **Support multi-format** : Chargement/sauvegarde en .dat et .json
- ✅ **Gestion des changements de produit** : Coûts d'inactivité/nettoyage
- ✅ **Optimisation avancée** : First-solution PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH

## 🚀 Installation

### Prérequis

- Python 3.7+
- OR-Tools

### Installation des dépendances

```bash
pip install ortools numpy
```

Ou utiliser le fichier requirements.txt:

```bash
pip install -r requirements.txt
```

## 📁 Structure des fichiers

```
src/
├── mpvrpcc_ortools_new.py       # Solveur principal avec OR-Tools
├── instance_manager.py           # Gestion import/export instances
├── test_ortools.py              # Interface de test interactive
├── test_mpvrpcc.py             # Tests unitaires
└── demo_ortools.py             # Exemples de démonstration
```

## 🎯 Utilisation

### 1. Interface interactive

```bash
python test_ortools.py
```

Permet de :
- Charger une instance existante (.dat ou .json)
- Créer une instance de test
- Résoudre et afficher les résultats

### 2. Utilisation par script

```python
from mpvrpcc_ortools_new import MPVRPCCORToolsSolver, SolutionFormatter
from instance_manager import InstanceManager

# Charger une instance
instance = InstanceManager.load_from_dat("instance.dat")

# Créer et résoudre
solver = MPVRPCCORToolsSolver(instance)
solution = solver.solve(time_limit=60, verbose=True)

# Récupérer les métriques
metrics = solver.get_metrics()

# Sauvegarder la solution
SolutionFormatter.write_solution(instance, solution, metrics, "solution.dat")
```

## 📊 Formats supportés

### Format DAT

```
NbProd NbDepots NbGarages NbStations NbVehicles
[Matrice coûts changement NbProd x NbProd]
[NbVehicles lignes : ID Capacité Garage_ID Prod_Init]
[NbDepots lignes : ID X Y Stock_P1 ... Stock_Pn]
[NbGarages lignes : ID X Y]
[NbStations lignes : ID X Y Demande_P1 ... Demande_Pn]
```

### Format JSON

```json
{
  "name": "instance_name",
  "garages": [{"id": 1, "x": 0, "y": 0, "name": "Garage_1"}],
  "depots": [{"id": 1, "x": 50, "y": 50, "stock": {"0": 100, "1": 100}}],
  "stations": [{"id": 1, "x": 10, "y": 10, "demand": {"0": 10, "1": 5}}],
  "trucks": [{"id": 1, "capacity": 50, "garage_id": 1, "initial_product": 0}],
  "changeover_costs": {"0-1": 10, "1-0": 10}
}
```

## 🔍 Classes principales

### `MPVRPCCORToolsSolver`

Solveur principal utilisant OR-Tools.

**Méthodes clés:**
- `solve(time_limit, verbose)` : Résout l'instance
- `get_metrics()` : Retourne les métriques de la solution
- `validate_solution()` : Valide les contraintes

### `MPVRPCCInstance`

Représente une instance du problème.

**Méthodes:**
- `add_garage(x, y, name)` : Ajoute un garage
- `add_depot(x, y, stock, name)` : Ajoute un dépôt
- `add_station(x, y, demand, name)` : Ajoute une station
- `add_truck(capacity, garage_id, initial_product)` : Ajoute un camion
- `validate_instance()` : Valide la cohérence

### `InstanceManager`

Gère l'import/export d'instances.

**Méthodes statiques:**
- `load_from_dat(filepath)` : Charge depuis un fichier .dat
- `load_from_json(filepath)` : Charge depuis un fichier .json
- `save_to_json(instance, filepath)` : Sauvegarde en JSON

### `SolutionFormatter`

Formate et exporte les solutions.

**Méthodes:**
- `write_solution(instance, solution, metrics, filename)` : Exporte en .dat
- `print_solution(instance, solution, metrics)` : Affichage lisible

## 📈 Exemple complet

```python
from mpvrpcc_ortools_new import *

# Créer une instance
instance = MPVRPCCInstance("demo")

# Ajouter les éléments
g1 = instance.add_garage(0, 0, "Garage_1")
d1 = instance.add_depot(50, 50, {0: 100, 1: 100}, "Depot_1")
s1 = instance.add_station(10, 10, {0: 10, 1: 5}, "Station_1")
t1 = instance.add_truck(50, g1, 0)

# Coûts de changement
instance.set_changeover_costs({
    (0, 0): 0, (0, 1): 10,
    (1, 0): 10, (1, 1): 0
})

# Résoudre
solver = MPVRPCCORToolsSolver(instance)
solution = solver.solve(time_limit=30, verbose=True)

# Afficher résultats
metrics = solver.get_metrics()
SolutionFormatter.print_solution(instance, solution, metrics)
```

## 🧪 Tests

### Test simple

```bash
python test_ortools.py
# Choisir option 2 (instance de test)
```

### Test avec fichier

```bash
python test_ortools.py
# Choisir option 1 et charger instance.dat ou instance.json
```

## 📊 Métriques de performance

La solution fournit :

- **num_vehicles** : Nombre de véhicules utilisés
- **num_product_changes** : Nombre de changements de produit
- **total_changeover_cost** : Coût total des changements
- **total_distance** : Distance totale parcourue
- **total_cost** : Coût global (distance + changements)
- **computation_time** : Temps de calcul en secondes

## 🔧 Configuration OR-Tools

### Paramètres d'optimisation

Les paramètres par défaut utilisent :
- **First Solution** : PATH_CHEAPEST_ARC (solution initiale rapide)
- **Local Search** : GUIDED_LOCAL_SEARCH (amélioration itérative)
- **Time Limit** : 50% du temps total disponible

### Personnalisation

Pour modifier les paramètres OR-Tools, éditer dans `_solve_vrp_for_product_ortools()`:

```python
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
search_parameters.time_limit.seconds = int(time_limit * 0.5)
```

## 🐛 Dépannage

### ImportError: No module named ortools

```bash
pip install ortools
```

### La solution n'est pas valide

Vérifier :
1. Stocks suffisants : `instance.validate_instance()`
2. Capacité totale adéquate
3. Demandes réalistes vs capacités

### Temps de calcul trop long

- Réduire `time_limit`
- Réduire le nombre de stations/camions pour les tests
- Simplifier les coûts de changement

## 📚 Références

- [OR-Tools Documentation](https://developers.google.com/optimization/routing)
- [Routing Library Guide](https://developers.google.com/optimization/routing/routing_library)

## 📝 Licence

Projet académique - Université (2026)

## 👤 Auteur

Modifié et intégré avec OR-Tools - 2026
