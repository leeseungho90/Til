# -*- coding:utf-8 -*-
import pandas as pd
from pgm.CONFIG import path_data_destinie
from pgm.Pension.Param.paramData import XmlReader
from datetime import datetime
import functools
import numpy as np

varcontrol = 'date[fin]'
m = varcontrol.split('[')
print m[0], m[1][:-1]

def list_param(regime, data, param_to_check):
    ''' Cette fonction ressort un dictionnaire des paramètres de la législation
    Lorsqu'un paramètre est spécifié par tranche, le vecteur des valeurs associées aux individus de data est stockée
    Le dictionnaire est accessible par appel de regime.valparam '''
    param =regime.ret_base 
    for k, v in param_to_check.items():
        if type(v) != float :
            control =  v.varcontrol
            # 1 - attribution des valeurs de la variable de contrôle
            if control.find('[') != -1 : 
                m = varcontrol.split('[')
                var = m[0]
                varcontrol = m[1][:-1]
                data = data.loc[data[²]]
                
            elif control.find('__') == -1: 
                 varcontrol = data[control]
                             
            if v.formatcontrol == 'date' : 
                varcontrol = varcontrol.astype(int).astype(str) + '-01-01'
                varcontrol = varcontrol.apply(lambda x : datetime.strptime(x,"%Y-%m-%d").date())   #data[str(getattr(v, 'varcontrol'))] 
            # 2 - Attributions des paramètres selon les valeurs des variables de contrôle
            if control.find('__') != -1:
                param_to_check[k + '_nb'] = v._nb
                for i in range(0, v._nb) :
                    param_to_check[k + str(i)] = getattr(v, 'tranche' + str(i))
                del param_to_check[k]
            else :
                val = np.zeros(len(varcontrol))
                for i in range(v._nb) :
                    value = getattr(v, 'tranche' + str(i))
                    seuilinf = getattr(v, 'tranche' + str(i)+ '_seuilinf')
                    seuilsup = getattr(v, 'tranche' + str(i)+ '_seuilsup')
                    bool_control = (varcontrol > seuilinf) & (varcontrol <= seuilsup)
                    #print sum(bool_control)
                    val +=  value* bool_control
                    param_to_check[k] = np.array(val)
            #data[k + str(regime)] = val
    setattr(regime, 'valparam', param_to_check)
    return param_to_check #, data



class Pension(object):
    """
    La classe qui permet de lancer le calcul des retraites
    """
    def __init__(self, date_simul, paramFile):
        self.regime = None
        self._date = date_simul
        self.paramFile = paramFile


    def load_param(self): 
        ''' Cette fonction permet de charger les paramètres relatifs à la législation de calcul des droits'''
        print "Début de l'importation des paramètres de la législation"
        read = XmlReader(self.paramFile, self._date)
        self.param = read.param
  
    def trim_cot(self):
        print "Calcul du nombre de trimestres côtisés"
        raise NotImplementedError()
    
    def sal_ref(self, nb_sam, emp):
        ''' Calcul du salaire de référence '''
        assert len(nb_sam) == len(emp.drop_duplicates('id'))
        
    
    def calculate_CP(self, trim_cot):
        ''' Calcul du coefficient de proratisation '''
        N_CP =  self.valparam['N_CP']
        CP = np.minimum(1, trim_cot / N_CP)
        return CP

    def calculate_taux(self, data):
        ''' Calcul générique du taux individuel avec décotes et surcotes éventuelles. Arguments : 
            - data : données d'entrée contenant param indiv (âge, trimestres cotisés par régime)
            - param : paramètres de la législation '''
        
        def _dum_date(date, seuil):
            if date <seuil:
                trim_to_taux = 0
            else:
                trim_to_taux = 1
                
            return int(trim_to_taux)
        
        def _cotes_annuelles(trim_cot, age, var, dic_var, trim_to_taux, age_ref):  
            test = var + '_nb'
            if var == 'decote':
                dum = -1
            if var == 'surcote' :
                dum = 1
                
            if test in dic_var.keys() :
                vec = np.zeros(len(dic_var['N_tau']))
                for i in range(dic_var[var + '_nb']) : 
                    to_vec = np.minimum(dum*(age - dic_var[age_ref] )/3, dum*(trim_cot - dic_var['N_tau'] - i*4))
                    vec += dic_var[var+str(i)] * np.maximum(0, to_vec*trim_to_taux)
            else:
                to_vec = np.minimum(dum*(age - dic_var[age_ref] )/3, dum*(trim_cot - dic_var['N_tau']))
                to_vec =  np.maximum(0, to_vec*trim_to_taux)
                vec = dic_var[var] *to_vec
            return vec
        
        reg =self.regime
        var = self.valparam
        age = data['agem']
        trim_cot = data['trim_tot']
        trim_to_taux = _dum_date(self._date, datetime.strptime("1983-01-01","%Y-%m-%d").date())
        decote = _cotes_annuelles(trim_cot, age, 'decote', var, trim_to_taux, 'age_decote')
        surcote = _cotes_annuelles(trim_cot, age, 'surcote', var, trim_to_taux, 'age_min')
        taux = var['tx_plein'] * (1 - decote + surcote)
        return taux
        