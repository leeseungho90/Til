# -*- coding:utf-8 -*-
from __future__ import print_function

'''
Created on 2 août 2013
@author: a.eidelman
'''

import numpy as np
from pandas import Series, DataFrame
from numpy.lib.stride_tricks import as_strided
import pandas as pd
import pdb

of_name_to_til=  {'ind':'person','foy':'declar','men':'menage', 'fam':'famille'}


def recode(table, var_in, var_out, list, method, dtype=None):
    '''
    code une variable à partir d'une autre
    attention à la liste et à son ordre pour des méthode avec comparaison d'ordre
    '''
    if var_in == var_out:
        raise Exception("Passer par une variable intermédiaire c'est plus safe")
    
    if dtype is None:
        dtype1 = table[var_in].dtype
        # dtype1 = table[var_in].max()
    
    table[var_out] = Series(dtype=dtype)
    for el in list:
        val_in = el[0]
        val_out = el[1]
        if method is 'geq':
            table[var_out][table[var_in]>=val_in] = val_out
        if method is 'eq':
            table[var_out][table[var_in]==val_in] = val_out
        if method is 'leq':
            table[var_out][table[var_in]<=val_in] = val_out                    
        if method is 'lth':
            table[var_out][table[var_in]< val_in] = val_out                      
        if method is 'gth':
            table[var_out][table[var_in]> val_in] = val_out  
        if method is 'isin':
            table[var_out][table[var_in].isin(val_in)] = val_out  

def index_repeated(nb_rep):
    '''
    Fonction qui permet de numeroter les réplications. Si [A,B,C] sont répliqués 3,4 et 2 fois alors la fonction retourne
    [0,1,2,0,1,2,3,0,1] qui permet ensuite d'avoir 
    [[A,A,A,B,B,B,B,C,C],[0,1,2,0,1,2,3,0,1]] et d'identifier les replications
    '''
    id_rep = np.arange(nb_rep.max())
    id_rep = as_strided(id_rep, shape=nb_rep.shape + id_rep.shape, strides=(0,) + id_rep.strides)
    return  id_rep[id_rep < nb_rep[:, None]]  

            
def replicate(table):
        columns_ini = table.columns   
        dtypes_ini = table.dtypes
        nb_rep_table = np.asarray(table['nb_rep'], dtype=np.int64)   
        table.to_csv('testcsv.csv', sep=';')
        
        table_exp = np.asarray(table).repeat(nb_rep_table, axis=0)
        table_exp = DataFrame(table_exp,  columns = columns_ini, dtype = float)

        # change pour avoir les dtype initiaux malgré le passage par numpy
        for type in [np.int64, np.int32, np.int16, np.int8, np.float32, np.float16]:
            var_type = dtypes_ini == type
            modif_types = dtypes_ini[var_type].index.tolist()
            table_exp[modif_types] = table_exp[modif_types].astype(type)
        
        table_exp['id_rep'] =  index_repeated(nb_rep_table)
        table_exp['id_ini'] = table_exp['id']
        table_exp['id'] = table_exp.index
        
        return table_exp

def new_link_with_men(table, table_exp, link_name):
        '''
        A partir des valeurs initiables de lien initial (link_name) replique pour avoir le bon nouveau lien 
        '''
        nb_by_table = np.asarray(table.groupby(link_name).size())
        #TODO: améliorer avec numpy et groupby ? 
        group_old_id = table_exp.ix[table_exp['id_ini'].isin(table[link_name]),['id_ini','id']].groupby('id_ini').groups.values()
        group_old_id = np.array(group_old_id)
        group_old_id =  group_old_id.repeat(nb_by_table)
        new_id = []
        for el in group_old_id: 
            new_id += el
        return new_id
    

def _MinType_col_int_pos(col):
    '''
    retourne le type minimal d'une serie d'entier positif
    on notera le -2 car on a deux valeurs prises par 0 et -1
    '''
    if max(abs(col)) < 2**8-2:
        return col.astype(np.int8)
    elif max(abs(col)) < 2**16-2:
        return col.astype(np.int16)
    elif max(abs(col)) < 2**32-2:
        return col.astype(np.int32)
    else:
        return col.astype(np.int64)

def minimal_dtype(table):
    '''
    Try to give columns the minimal type using -1 for NaN value
    Variables with only two non null value are put into boolean asserting NaN value as False
    Minimal type for float is not searched (only integer)
    When integer has positive and negative value, there is no obvious default value for NaN values so nothing is done.
    '''
    assert isinstance(table, pd.DataFrame)
    modif = {'probleme':[], 'boolean':[], 'int_one_sign':[], 'other_int':[], 'float':[], 'object':[]}
    for colname in table.columns:
        col = table[colname]
        if len(col.value_counts()) <= 1:
            #TODO: pour l'instant bug si la valeur de départ était -1
            col = col.fillna(value=-1)
            modif['probleme'].append(colname)
        if col.dtype == 'O':
            # print(colname," is an object, with a good dictionnary, we could transform it into integer")
            modif['object'].append(colname)
        if col.dtype != 'O':
            if len(col.value_counts()) == 2:
                min = col.min()
                col = col.fillna(value=min)
                try:
                    col = col - min
                except:
                    pdb.set_trace()
                modif['boolean'].append(colname)
                table[colname] = col.astype(np.bool)
            else:
                try:
                    if (col[col.notnull()].astype(int) == col[col.notnull()]).all():
                        col[col.notnull()] = col[col.notnull()].astype(int)
                        if col.min() > 0 or col.max() < 0 : # un seul signe pour les valeurs
                            sign =1-2*(max(col) < 0)
                            col = col.fillna(value=-1*sign)
                            modif['int_one_sign'].append(colname)
                            table[colname] = _MinType_col_int_pos(col)
                        else:
                            modif['other_int'].append(colname)
                    else:
                        if (col.isnull().any()):
                            modif['float'].append(colname)
                        else:
                            #TODO
                            modif['float'].append(colname)
                except:
                    pdb.set_trace()
    
    print('Object type columns have not been modified : \n ', modif['object'])
    print('Float type columns have not been modified : \n ', modif['float'])
    print('Integer type columns with positive AND negative values have not been modified : \n ', modif['other_int'])
    print('There is no much distinct values for following variables : \n ', modif['probleme'])
    print('Note that these columns are transformed into boolean : \n ', modif['boolean'])
    print('Note also that in these cases, missing value are set to False')
    print('Dtype have been also optimized for : \n', modif['int_one_sign'] )
    print('Missing values were set to -1 (or +1 when only negative values)')

    return table



