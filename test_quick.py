#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test rapide du solveur OR-Tools
"""

import sys
sys.path.insert(0, 'src')

from mpvrpcc_ortools_new import MPVRPCCORToolsSolver, MPVRPCCInstance, SolutionFormatter

# Créer une instance simple
print("🔨 Création d'une instance de test...")
instance = MPVRPCCInstance("Test_Simple")

# Garage
instance.add_garage(0, 0, "Garage")

# Dépôt
instance.add_depot(50, 50, {0: 100, 1: 100}, "Depot")

# 4 stations
stations = [
    (10, 10, {0: 20, 1: 0}),
    (20, 20, {0: 15, 1: 10}),
    (80, 80, {0: 0, 1: 25}),
    (90, 90, {0: 10, 1: 15}),
]

for i, (x, y, demand) in enumerate(stations):
    instance.add_station(x, y, demand, f"Station_{i+1}")

# 2 camions
instance.add_truck(50, 1, 0)
instance.add_truck(50, 1, 1)

# Coûts de changement
instance.set_changeover_costs({
    (0, 0): 0, (0, 1): 20,
    (1, 0): 20, (1, 1): 0
})

# Valider
print("✅ Validation de l'instance...")
valid, errors = instance.validate_instance()
if not valid:
    print("❌ Instance invalide!")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)

# Résoudre
print("🚀 Résolution avec OR-Tools...")
solver = MPVRPCCORToolsSolver(instance)
solution = solver.solve(time_limit=30, verbose=True)

# Afficher résultats
metrics = solver.get_metrics()
print(f"\n{'='*60}")
print(f"RÉSULTATS FINAUX")
print(f"{'='*60}")
print(f"Coût total    : {metrics['total_cost']:.2f}")
print(f"Distance      : {metrics['total_distance']:.2f} km")
print(f"Changements   : {metrics['num_product_changes']}")
print(f"Véhicules     : {metrics['num_vehicles']}")
print(f"Temps calcul  : {metrics['computation_time']:.3f}s")

# Valider la solution
print(f"\n{'='*60}")
valid_sol, sol_errors = solver.validate_solution()
if valid_sol:
    print("✅ SOLUTION VALIDE")
else:
    print("❌ Erreurs dans la solution:")
    for err in sol_errors:
        print(f"  - {err}")

print(f"{'='*60}")
