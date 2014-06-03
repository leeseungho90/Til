# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import sys
import datetime as dt
import time

from CONFIG import path_pension
sys.path.append(path_pension)

from Regimes.Fonction_publique import FonctionPublique
from Regimes.Regimes_complementaires_prive import AGIRC, ARRCO
from Regimes.Regimes_prives import RegimeGeneral, RegimeSocialIndependants
from time_array import TimeArray
from pension_data import PensionData
from utils_pension import build_naiss, load_param
from pension_functions import select_regime_base, sum_by_regime, update_all_regime
first_year_sal = 1949 
import cProfile

base_regimes = ['RegimeGeneral', 'FonctionPublique', 'RegimeSocialIndependants']
complementaire_regimes = ['ARRCO', 'AGIRC']
base_to_complementaire = {'RegimeGeneral': ['arrco', 'agirc'], 'FonctionPublique': []}

def til_pension(sali, workstate, info_ind, time_step='year', yearsim=2009, yearleg=None, example=False):
    command = """run_pension(sali, workstate, info_ind, time_step, yearsim, yearleg, example)"""
    cProfile.runctx( command, globals(), locals(), filename="profile_pension" + str(yearsim))

def run_pension(sali, workstate, info_ind, time_step='year', yearsim=2009, yearleg=None, to_check=False):
    if yearsim > 2009: 
        yearsim = 2009
    # I - Chargement des paramètres de la législation (-> stockage au format .json type OF) + des tables d'intéret
    # Pour l'instant on lance le calcul des retraites pour les individus ayant plus de 62 ans (sélection faite dans exprmisc de Til\liam2)
    param_file = path_pension + '\\France\\param.xml' #TODO: Amelioration
    try: 
        assert all(sali.index == workstate.index) and all(sali.index == info_ind.index)
    except:
        assert all(sali.index == workstate.index)
        assert len(sali) == len(info_ind)
        sal = sali.index
        idx = info_ind.index
        assert all(sal[sal.isin(idx)] == idx[idx.isin(sal)])
        print(sal[~sal.isin(idx)])
        print(idx[~idx.isin(sal)])
        
        # un décalage ?
        decal = idx[~idx.isin(sal)][0] - sal[~sal.isin(idx)][0]
        import pdb
        pdb.set_trace()
        
    dict_to_check = dict()
    ##TODO: should be done before
    assert sali.columns.tolist() == workstate.columns.tolist()
    assert sali.columns.tolist() == (sorted(sali.columns))
    dates = sali.columns.tolist()
    sali = np.array(sali)
    workstate = np.array(workstate)
    
    sali = TimeArray(sali, dates, name='sali')
    sali.selected_dates(first=first_year_sal, last=yearsim, inplace=True)
    workstate = TimeArray(workstate, dates, name='workstate')
    workstate.selected_dates(first=first_year_sal, last=yearsim, inplace=True) 

    if max(info_ind.loc[:,'sexe']) == 2:
        info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(1,0)
        info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(2,1)
    info_ind.loc[:,'naiss'] = build_naiss(info_ind.loc[:,'agem'], dt.date(yearsim,1,1))
    
    data = PensionData(workstate, sali, info_ind, yearsim)
    
    # Si aucune année n'est renseignée pour la législation on prend l'année de simulation
    if yearleg is None:
        yearleg = yearsim
    date_param = str(yearleg)+ '-05-01' #TODO: change for -01-01 ?
    
    date_param = dt.datetime.strptime(date_param ,"%Y-%m-%d").date()
    P, P_longit = load_param(param_file, info_ind, date_param)
    config = {'dateleg' : yearleg, 'P': P, 'P_longit': P_longit, 'dates': dates, 'index': info_ind.index,
              'time_step': time_step, 'data_type': 'numpy', 'first_year': first_year_sal}       
    ### get trimesters (only TimeArray with trim by year), wages (only TimeArray with wage by year) and trim_maj (only vector of majoration): 
    trimesters_wages = dict()
    to_other = dict()
    for reg_name in base_regimes:
        reg = eval(reg_name + '()')
        reg.set_config(**config)
        trimesters_wages_regime, to_other_regime = reg.get_trimesters_wages(data)
        trimesters_wages[reg_name] = trimesters_wages_regime
        to_other.update(to_other_regime)
        
    trimesters_wages = sum_by_regime(trimesters_wages, to_other)
    trimesters_wages = update_all_regime(trimesters_wages, dict_to_check)
    
    for reg_name in base_regimes:
        reg = eval(reg_name + '()')
        reg.set_config(**config)
        pension_reg = reg.calculate_pension(data, trimesters_wages[reg_name], trimesters_wages['all_regime'], dict_to_check)
        if to_check == True:
            dict_to_check['pension_' + reg.regime] = pension_reg

    for reg_name in complementaire_regimes:
        reg = eval(reg_name + '()')
        reg.set_config(**config)
        regime_base = select_regime_base(trimesters_wages, reg.regime, base_to_complementaire)
        pension_reg = reg.calculate_pension(data, regime_base['trimesters'], dict_to_check)
        if to_check == True:
            dict_to_check['pension_' + reg.regime] = pension_reg
    if to_check == True:
        #pd.DataFrame(to_check).to_csv('resultat2004.csv')
        return pd.DataFrame(dict_to_check)
    else:
        return pension_reg # TODO: define the output