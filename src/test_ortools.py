# -*- coding: utf-8 -*-
"""
Script de test interactif pour MPVRP-CC avec OR-Tools
Compatible avec les formats DAT et JSON
"""

import os
import sys
import time
from mpvrpcc_ortools_new import MPVRPCCORToolsSolver, SolutionFormatter, MPVRPCCInstance
from instance_manager import InstanceManager


def run_test_process(instance: MPVRPCCInstance, name, time_limit):
    """Exécute la validation, la résolution et la sauvegarde"""
    print(f"\n--- Analyse de l'instance : {name} ---")
    
    # Validation structurelle
    valid, errors = instance.validate_instance()
    if not valid:
        print("❌ Instance invalide :")
        for err in errors:
            print(f"   - {err}")
        return

    print(f"✅ Configuration : {len(instance.products)} Produits, {len(instance.trucks)} Camions")
    print(f"✅ Sites : {len(instance.depots)} Dépôts, {len(instance.stations)} Stations")
    
    # Initialisation du solveur OR-Tools
    solver = MPVRPCCORToolsSolver(instance)
    print(f"🚀 Résolution avec OR-Tools (limite {time_limit}s)...")
    
    try:
        start_time = time.time()
        solution = solver.solve(time_limit=time_limit, verbose=True)
        metrics = solver.get_metrics()
        
        # Validation de la solution trouvée
        valid_sol, sol_errors = solver.validate_solution()
        if not valid_sol:
            print("❌ La solution trouvée ne respecte pas les contraintes métiers.")
            for err in sol_errors:
                print(f"   - {err}")
            return

        print("\n🏆 RÉSULTATS OPTIMISATION (OR-Tools) :")
        print(f"  • Coût total : {metrics['total_cost']:.2f}")
        print(f"  • Distance parcourue : {metrics['total_distance']:.2f} km")
        print(f"  • Nettoyages citernes : {metrics['num_product_changes']}")
        print(f"  • Temps de calcul : {metrics['computation_time']:.3f}s")
        
        # Exportation des résultats
        output = os.path.join("solutions", f"Sol_{name}")
        SolutionFormatter.write_solution(instance, solution, metrics, output)
        print(f"💾 Rapport généré : {output}")
        
        # Afficher la solution détaillée
        SolutionFormatter.print_solution(instance, solution, metrics)
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du solveur : {e}")
        import traceback
        traceback.print_exc()


def main_menu():
    """Interface utilisateur pour le chargement des fichiers"""
    while True:
        print("\n" + "="*60)
        print("      INTERFACE DE TEST MPVRP-CC AVEC OR-TOOLS")
        print("="*60)
        print("1. Charger une instance (.dat ou .json)")
        print("2. Créer une instance de test simple")
        print("3. Quitter")
        
        choix = input("\nVotre choix : ").strip()
        
        if choix == "3":
            print("Fermeture du programme.")
            break
        
        if choix == "2":
            print("\n📋 Création d'une instance de test...")
            instance = _create_test_instance()
            t_limit = input("Limite de temps (secondes, défaut 30) : ").strip()
            t_limit = int(t_limit) if t_limit.isdigit() else 30
            run_test_process(instance, "test_instance", t_limit)
            input("\nAppuyez sur Entrée pour continuer...")
            
        elif choix == "1":
            path = input("Chemin du fichier d'instance : ").strip()
            
            if not os.path.exists(path):
                print(f"❌ Erreur : Le fichier '{path}' est introuvable.")
                continue
            
            try:
                # Appel au gestionnaire d'instance selon l'extension
                if path.lower().endswith('.json'):
                    instance = InstanceManager.load_from_json(path)
                elif path.lower().endswith('.dat'):
                    instance = InstanceManager.load_from_dat(path)
                else:
                    print("❌ Format non supporté. Utilisez uniquement .json ou .dat.")
                    continue
                
                # Paramétrage de la durée
                t_limit = input("Limite de temps (secondes, défaut 30) : ").strip()
                t_limit = int(t_limit) if t_limit.isdigit() else 30
                
                run_test_process(instance, os.path.basename(path), t_limit)
                
            except Exception as e:
                print(f"❌ Échec du chargement : {e}")
                import traceback
                traceback.print_exc()
            
            input("\nAppuyez sur Entrée pour continuer...")


def _create_test_instance() -> MPVRPCCInstance:
    """Crée une instance de test simple"""
    instance = MPVRPCCInstance("test_small")
    
    # Créer 2 garages
    instance.add_garage(0, 0, "Garage_1")
    instance.add_garage(100, 100, "Garage_2")
    
    # Créer 2 dépôts
    instance.add_depot(50, 50, {0: 100, 1: 100}, "Depot_1")
    instance.add_depot(60, 60, {0: 100, 1: 100}, "Depot_2")
    
    # Créer 8 stations
    stations_coords = [
        (10, 10), (20, 20), (30, 30), (40, 40),
        (70, 70), (80, 80), (90, 90), (100, 100)
    ]
    
    for i, (x, y) in enumerate(stations_coords):
        demand = {0: 10, 1: 10} if i < 4 else {0: 10}
        instance.add_station(x, y, demand, f"Station_{i+1}")
    
    # Créer 3 camions
    instance.add_truck(50, 1, 0)
    instance.add_truck(50, 1, 0)
    instance.add_truck(50, 2, 0)
    
    # Coûts de changement de produit
    changeover_costs = {
        (0, 0): 0.0, (0, 1): 10.0,
        (1, 0): 10.0, (1, 1): 0.0
    }
    instance.set_changeover_costs(changeover_costs)
    
    return instance


if __name__ == "__main__":
    main_menu()
