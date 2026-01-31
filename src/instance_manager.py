# -*- coding: utf-8 -*-
"""
Gestionnaire d'instances MPVRP-CC - Version Import/Export
Permet de charger et sauvegarder des instances aux formats JSON et DAT.
Support pour OR-Tools.
"""

import json
import os
from typing import Dict, List
# Import du solveur OR-Tools
from mpvrpcc_ortools_new import MPVRPCCInstance

class InstanceManager:
    """Gestionnaire dédié exclusivement à l'importation et l'exportation d'instances"""
  
    @staticmethod
    def load_from_dat(filepath: str) -> MPVRPCCInstance:
        """
        Charge une instance MPVRP-CC à partir d'un fichier .dat positionnel.
        Format attendu :
        Ligne 1 : NbProd NbGarages NbDepots NbStations NbVehicles
        Suivi des matrices de coûts, camions, dépôts et stations.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            # On filtre les commentaires et les lignes vides
            lines = [l.strip() for l in f if l.strip() and not l.startswith(('#', '"'))]

        if not lines:
            raise ValueError("Le fichier .dat est vide ou invalide.")

        # 1. Lecture de l'en-tête (Ligne 1)
        header = list(map(int, lines[0].split()))
        nb_prod, nb_depots, nb_garages, nb_stations, nb_vehicles = header
        
        instance = MPVRPCCInstance(os.path.basename(filepath))
        current_line = 1

        # 2. Lecture de la matrice de coûts de changement (Changeover)
        # On lit 'nb_prod' lignes pour la matrice
        co_costs = {}
        for i in range(nb_prod):
            costs = list(map(float, lines[current_line].split()))
            for j, cost in enumerate(costs):
                co_costs[(i, j)] = cost
            current_line += 1
        instance.set_changeover_costs(co_costs)

        # 3. Lecture des Camions (NbVehicles lignes)
        # Format : ID Capacité Garage_ID Prod_Init
        for _ in range(nb_vehicles):
            parts = list(map(float, lines[current_line].split()))
            instance.add_truck(
                capacity=parts[1], 
                garage_id=int(parts[2]), 
                initial_product=int(parts[3]) - 1 # -1 si les produits commencent à 1 dans le .dat
            )
            current_line += 1

        # 4. Lecture du/des Dépôts (NbDepots lignes)
        # Format : ID X Y Stock_P1 Stock_P2 ...
        for _ in range(nb_depots):
            parts = list(map(float, lines[current_line].split()))
            stock = {p: parts[3 + p] for p in range(nb_prod)}
            instance.add_depot(x=parts[1], y=parts[2], stock=stock, name=f"Depot_{int(parts[0])}")
            current_line += 1

        # 5. Lecture des Garages (NbGarages lignes)
        # Note : Si votre fichier n'a pas de bloc dédié, on utilise les coordonnées du dépôt 
        # ou des coordonnées par défaut pour le garage.
        for g_idx in range(nb_garages):
            parts = list(map(float, lines[current_line].split()))
            instance.add_garage(x=parts[1], y=parts[2], name=f"Garage_{int(parts[0])}")
            current_line += 1

        # 6. Lecture des Stations (NbStations lignes)
        # Format : ID X Y Demande_P1 Demande_P2 ...
        for _ in range(nb_stations):
            parts = list(map(float, lines[current_line].split()))
            demand = {p: parts[3 + p] for p in range(nb_prod) if parts[3 + p] > 0}
            instance.add_station(x=parts[1], y=parts[2], demand=demand, name=f"Station_{int(parts[0])}")
            current_line += 1

        return instance
    
    @staticmethod
    def load_from_json(filepath: str) -> MPVRPCCInstance:
        """
        Charge une instance MPVRP-CC à partir d'un fichier .json
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        instance = MPVRPCCInstance(os.path.basename(filepath))
        
        # Charger les garages
        for garage in data.get('garages', []):
            instance.add_garage(garage['x'], garage['y'], garage.get('name', ''))
        
        # Charger les dépôts
        for depot in data.get('depots', []):
            instance.add_depot(depot['x'], depot['y'], depot['stock'], depot.get('name', ''))
        
        # Charger les stations
        for station in data.get('stations', []):
            instance.add_station(station['x'], station['y'], station['demand'], station.get('name', ''))
        
        # Charger les camions
        for truck in data.get('trucks', []):
            instance.add_truck(truck['capacity'], truck['garage_id'], truck.get('initial_product', 0))
        
        # Charger les coûts de changement
        changeover_costs = {}
        for key, cost in data.get('changeover_costs', {}).items():
            # Les clés sont en format "prod1-prod2"
            prod_from, prod_to = map(int, key.split('-'))
            changeover_costs[(prod_from, prod_to)] = cost
        instance.set_changeover_costs(changeover_costs)
        
        return instance
    
    @staticmethod
    def save_to_json(instance: MPVRPCCInstance, filepath: str):
        """
        Sauvegarde une instance MPVRP-CC au format JSON
        """
        data = {
            'name': instance.name,
            'garages': [
                {'id': g.id, 'x': g.x, 'y': g.y, 'name': g.name}
                for g in instance.garages
            ],
            'depots': [
                {'id': d.id, 'x': d.location.x, 'y': d.location.y, 'stock': d.stock, 'name': d.location.name}
                for d in instance.depots
            ],
            'stations': [
                {'id': s.id, 'x': s.location.x, 'y': s.location.y, 'demand': s.demand, 'name': s.location.name}
                for s in instance.stations
            ],
            'trucks': [
                {'id': t.id, 'capacity': t.capacity, 'garage_id': t.garage_id, 'initial_product': t.initial_product}
                for t in instance.trucks
            ],
            'changeover_costs': {
                f"{k[0]}-{k[1]}": v for k, v in instance.changeover_costs.items()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)