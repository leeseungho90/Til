# -*- coding:utf-8 -*-
'''
Ce programme précise les comportements de départ à la retraite
'''

import pandas as pd
import numpy as np
from pgm.Pension.Calculate.pension import list_param


def exogene(regime, data, condition ='None'):
    ''' Cette fonction permet d'appeler un comportement de départ à la retraite exogène :
    Les personnes partent à la retraite dès lors que la condition d'âge ou de taux plein est remplie '''
    param = regime.ret_base
    data = data[data['trim_' + regime.regime] != 0]
    if (condition == 'age_min'): 
        if (type(param.age_min) != float) : 
            var = list_param(regime, data, {'age_min' : param.age_min})
            data['age_min'] = var['age_min']
            data = data[data['agem'] >= data['age_min']]
            data.drop('age_min', axis=1 )
        else :
            data = data[data['agem'] >= param.age_min]
    if (condition == 'tx_plein') | (condition == None) :
        var = list_param(regime, data, {'age_min' : param.age_min, 'N_tau': param.N_tau})
        print var
    if (condition == 'age_max'): 
        if (type(param.age_max) != float) : 
            var = list_param(regime, data, {'age_max' : param.age_max})
            data['age_max'] = var['age_max']
            data = data[data['agem'] >= data['age_max']]
        else :
            data = data[data['agem'] >= param.age_max]
        data.drop('age_max', axis=1 )  
    print "Nombre de personnes pour lesquelles on calcule une pension (avec option", condition, ") : ", len(data)
    return data, data['id'].reset_index()

def calculate_sam(nb_sam, emp, ident, date):
    sam = np.zeros(len(ident))
    for i in range(len(ident)):
        id =  ident['id'][i]
        nb =  nb_sam[i]*12
        val = emp['sali'][(emp['period'] <= date) & (emp['id'] == id) & (emp['workstate'].isin([3,4]))] 
        if (nb < len(val)) :
            val = val[-nb :]
        sam[i] = np.mean(val)
    return sam
        