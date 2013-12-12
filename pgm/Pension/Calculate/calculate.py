# -*- coding:utf-8 -*-
'''
Ce programme appel les fonctions de calcul des droits pour les différents régimes
'''
import pdb
import pandas as pd
import numpy as np
from pandas import merge
from pgm.CONFIG import path_data_destinie
from Regime_general import Regime_gene
from pension import Pension, list_param
from datetime import datetime
from pgm.Pension.Behavior.Behavior import exogene, calculate_sam

# ETAPE 0 : Construction d'une table test comportant (calcul des droits à retraite pour 2009 + pour l'instant aucun comportement de départ juste le calcul ):
# - 1 : les informations sur déroulés de carrières brutes issues de Destinie (pas mensuel artificiel)
# emp_Destinie est le déroulé des carrières de Destinie (travail jusqu'à la mort d'où les aberrations trouvées) mis en forme par Destinie.py
# le travail sur cette base vise a déterminée le nombre de données empiv minimales à conserver pour le calcul des droits

'''
emp = np.genfromtxt(path_data_destinie + 'emp_Destinie.csv', delimiter =',')
# - 2 - les informations individuelles de 2009 (année de l'enquête) telles qu'elles sont juste avant le lancement de la simulation

emp_month = np.repeat(emp, 12, axis=0)
emp = pd.DataFrame(emp_month, columns = ['index', 'id', 'period', 'workstate', 'sali'])
emp = emp[['id', 'period', 'workstate', 'sali']]
id_list = emp.loc[emp['period'] == 2009, 'id'].drop_duplicates('id')
emp = emp[(emp['id'].isin(id_list))] 
emp = emp[emp['period'] < 2010 ]
emp = emp.astype(int)
emp = emp.sort(['id', 'workstate'])
emp = emp.loc[~(emp['workstate'].isin([0,1])), :]
len_emp = len(emp)
emp = emp.sort(['id','period'])


months = []
for i in range(len_emp/12) :
    months += range(1,13)

emp['period'] = emp['period']*100 + months
emp.sort(['id', 'period']).to_csv('emp.csv')
'''

emp = pd.read_csv('emp.csv')
ind = pd.read_csv('indfinal.csv')
ind['id'] = ind.index

ind = ind.loc[ (ind['age']< 71)]
print sum(~(ind['workstate'].isin([0,1])))

# 1- Calculs des durées de cotisation par régimes + durée tot
# TO DO : Le but de cette étape à terme est de réduire la table ind à une table pension
# ne contenant que l'information strictement nécessaire pour le calcul des droits à retraite, tous régimes confondus

trim = emp.groupby(['id', 'workstate']).size()
trim = trim.reset_index()
trim[0] = trim[0].values /3 
pension = trim.drop_duplicates('id')

pension.index = pension['id'].astype(int)
print  len(pension)
regimes = {'chom': 2, 'ncadre':3, 'cadre' : 4, 'FPA': 5, 'FPS': 6, 'indep': 7, 'avpf': 8, 'preret':9 }
pension['trim_tot'] = 0
for reg in regimes:
    code = regimes[reg]
    id_reg = trim.loc[trim['workstate'] == code, 'id']
    trim_reg = trim.loc[trim['workstate'] == code, 0]
    pension['trim_'+ reg] = 0
    pension['trim_' + reg][id_reg] = trim_reg
    pension['trim_tot'] = pension['trim_tot'] +  pension['trim_' + reg]
    
pension = pension.drop(['workstate', 0], 1)
#pension.to_csv('pension.csv')
indf = merge(ind, pension, on = 'id', how = 'left').fillna(0)
indf['trim_RG'] = indf['trim_cadre'] + indf['trim_ncadre']

# 2 - Appel des fonctions de calcul de droits à la retraite pour individus avec durées non nulles pour régime
# TO DO : faire tourner les fonctions avec conditions sur les trim_reg != 0 

regimes = {'chom': 2, 'ncadre':3, 'cadre' : 4, 'FPA': 5, 'FPS': 6, 'indep': 7, 'avpf': 8, 'preret':9 }

# 2a - Calcul des taux par régimes
paramFile = 'param.xml'
date_simul = datetime.strptime("2012-01-02","%Y-%m-%d").date()

# (1) - Régime général
import time
start = time.time()
RG = Regime_gene(date_simul, paramFile)
# 1.1 Chargement des paramètres de la législation
RG.load_param()

# 1.2 Sélection des individus partant en retraite
t1 = time.time()
data, ident = exogene(RG, indf, condition = 'age_min')
# TODO: réattribué les trimestres FP au RG si en dessous des durées cibles de cotisations  
#data = indf
param = RG.ret_base
param_to_check = {'tx_plein' : param.tx_plein, 'age_min' : param.age_min, 'age_max' : param.age_max, 'decote' : param.decote, 
                  'surcote' : param.surcote, 'age_decote' : param.age_decote, 'N_tau': param.N_tau, 'N_CP': param.N_CP, 'nb_sam': param.nb_sam, 'mda_educ' : param.mda_educ, 'mda_naiss' : param.mda_naiss}
list_param(RG, data, param_to_check)
var = RG.valparam
print RG.valparam

# 1.3 Calcul des pensions
t2 = time.time()
data['nb_enf_educ'] = data['nb_enf']
data['trim_RG'] += RG.MDA(data)
taux = RG.calculate_taux( data)
CP = RG.calculate_CP(data['trim_RG'], data['agem'])
print (time.time() - t3)
sal = calculate_sam(var['nb_sam'], emp, ident, 201201)
print (time.time() - t3)
data['pension_RG'] = taux*CP*sal
data['taux_RG'] =  taux
data['CP_RG'] = CP
data['sal_ref_RG'] = sal
t4 = time.time()
data.to_csv('indtest.csv')

print "Temps :", (t1 - start), (t2 -t1), (t3 - t2), (t4 -t3), (time.time() - t4)
