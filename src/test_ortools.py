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


def test_folder_instances(folder_path: str, time_limit: int):
    """Teste toutes les instances d'un dossier"""
    valid_instances = []
    invalid_instances = []
    solution_folder = "solution_instances"
    
    # Créer le dossier de solutions s'il n'existe pas
    os.makedirs(solution_folder, exist_ok=True)
    
    print(f"\n📂 Scan du dossier : {folder_path}")
    
    if not os.path.isdir(folder_path):
        print(f"❌ Le dossier '{folder_path}' n'existe pas.")
        return
    
    # Parcourir tous les fichiers du dossier
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.dat', '.json'))]
    
    if not files:
        print(f"❌ Aucun fichier .dat ou .json trouvé dans '{folder_path}'")
        return
    
    print(f"🔍 Fichiers trouvés : {len(files)}\n")
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        print(f"➜ Traitement : {filename}...", end=" ")
        
        try:
            # Charger l'instance
            if filename.lower().endswith('.json'):
                instance = InstanceManager.load_from_json(filepath)
            else:
                instance = InstanceManager.load_from_dat(filepath)
            
            # Valider l'instance
            valid, errors = instance.validate_instance()
            
            if not valid:
                print(f"❌ Instance invalide")
                invalid_instances.append((filename, errors))
                continue
            
            print(f"✅ Validation OK - Résolution...", end=" ")
            
            # Résoudre l'instance
            solver = MPVRPCCORToolsSolver(instance)
            solution = solver.solve(time_limit=time_limit, verbose=False)
            metrics = solver.get_metrics()
            
            # Valider la solution
            valid_sol, sol_errors = solver.validate_solution()
            
            if not valid_sol:
                print(f"❌ Solution invalide")
                invalid_instances.append((filename, sol_errors))
                continue
            
            # Sauvegarder la solution
            output_path = os.path.join(solution_folder, f"Sol_{filename}")
            SolutionFormatter.write_solution(instance, solution, metrics, output_path)
            
            print(f"💾 Solution sauvegardée")
            valid_instances.append({
                'filename': filename,
                'num_products': len(instance.products),
                'num_trucks': len(instance.trucks),
                'num_depots': len(instance.depots),
                'num_stations': len(instance.stations),
                'total_cost': metrics['total_cost'],
                'computation_time': metrics['computation_time']
            })
            
        except Exception as e:
            print(f"❌ Erreur : {str(e)}")
            invalid_instances.append((filename, [str(e)]))
    
    # Afficher le résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DES INSTANCES")
    print("="*70)
    print(f"\n✅ INSTANCES VALIDES : {len(valid_instances)}")
    
    if valid_instances:
        print(f"\n{'Fichier':<30} {'Produits':<10} {'Camions':<10} {'Coût':<12} {'Temps(s)':<10}")
        print("-" * 70)
        for inst in valid_instances:
            print(f"{inst['filename']:<30} {inst['num_products']:<10} {inst['num_trucks']:<10} "
                  f"{inst['total_cost']:<12.2f} {inst['computation_time']:<10.3f}")
    
    print(f"\n❌ INSTANCES INVALIDES : {len(invalid_instances)}")
    if invalid_instances:
        for filename, errors in invalid_instances:
            print(f"  • {filename}")
            for err in errors[:2]:  # Afficher max 2 erreurs
                print(f"    - {err}")
    
    print(f"\n💾 Solutions sauvegardées dans : {solution_folder}/")
    print("="*70)


def main_menu():
    """Interface utilisateur pour le chargement des fichiers"""
    while True:
        print("\n" + "="*60)
        print("      INTERFACE DE TEST MPVRP-CC AVEC OR-TOOLS")
        print("="*60)
        print("1. Charger une instance (.dat ou .json)")
        print("2. Créer une instance de test simple")
        print("3. Tester toutes les instances d'un dossier")
        print("4. Quitter")
        
        choix = input("\nVotre choix : ").strip()
        
        if choix == "4":
            print("Fermeture du programme.")
            break
        
        if choix == "2":
            print("\n📋 Création d'une instance de test...")
            instance = _create_test_instance()
            t_limit = input("Limite de temps (secondes, défaut 30) : ").strip()
            t_limit = int(t_limit) if t_limit.isdigit() else 30
            run_test_process(instance, "test_instance", t_limit)
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choix == "3":
            folder = input("Chemin du dossier d'instances : ").strip()
            t_limit = input("Limite de temps (secondes, défaut 30) : ").strip()
            t_limit = int(t_limit) if t_limit.isdigit() else 30
            test_folder_instances(folder, t_limit)
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
