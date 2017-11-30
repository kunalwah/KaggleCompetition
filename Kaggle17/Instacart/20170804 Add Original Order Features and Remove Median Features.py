# -*- coding: utf-8 -*-
"""
Created on Fri Aug  4 19:43:37 2017

@author: Jiashen Liu

Purpose: 去掉median特征，同时join会订单原有特征看看！
之前在做的时候一直在忽略原生特征
"""

from functions_in import *
import pandas as pd
import numpy as np
import time

DIR = 'data/'
W2C = pd.read_csv('data/WORD2VEC_Feat.csv')
ostreak = pd.read_csv(DIR+'order_streaks.csv')
priors, train, orders, products, aisles, departments, sample_submission = load_data(DIR)
product_name = pd.read_csv(DIR+'product_name_pca_2comp.csv')
print('Begin')
print(time.ctime())

## detail表里记录这以前所有订单的信息
priors_orders_detail = orders.merge(right=priors, how='inner', on='order_id')

#新特征
# _user_buy_product_times: 用户是第几次购买该商品
priors_orders_detail.loc[:,'_user_buy_product_times'] = priors_orders_detail.groupby(['user_id', 'product_id']).cumcount() + 1

"""
特征组1：产品组。主要看：在之前的订单记录中，产品的一些特性
_prod_tot_cnts： 产品被买的次数
_prod_reorder_tot_cnts：产品被回购的总次数
_prod_buy_first_time_total_cnt：产品被首次购买的次数
_prod_buy_second_time_total_cnt：产品被二次购买的次数
_prod_mean_cart_order：产品被放入购物篮顺序的均值
_prod_std_cart_order：产品被放入购物篮顺序的标准差
_prod_median_cart_order:产品被放入顺序的中位数
_prod_reorder_prob：不好理解，看特征重要性再说
_prod_reorder_ratio：回购率
_prod_reorder_times：产品被回购的次数？？不好理解，看重要性
_prod_dow_*,_prod_hod_*,'_prod_days_since'，：三个大类指标分别去衡量产品被订购的时间和日期，以及产品
被上次购买的信息
"""


agg_dict = {'user_id':{'_prod_tot_cnts':'count'}, 
            'reordered':{'_prod_reorder_tot_cnts':'sum'}, 
            '_user_buy_product_times': {'_prod_buy_first_time_total_cnt':lambda x: sum(x==1),
                                        '_prod_buy_second_time_total_cnt':lambda x: sum(x==2)},
            'add_to_cart_order':{'_prod_mean_cart_order':'mean',
                                '_prod_std_cart_order':'std'},
             'order_dow':{'_prod_mean_dow':'mean',
                          '_prod_std_dow':'std'},
              'order_hour_of_day':{'_prod_mean_hod':'mean',
                                   '_prod_std_hod':'std'},
               'days_since_prior_order':{
                                        '_prod_sum_days_since_prior_order':'sum', 
                                        '_prod_mean_days_since_prior_order': 'mean',
                                        '_prod_std_days_since_prior_order':'std'
                                         }}
prd = ka_add_groupby_features_1_vs_n(priors_orders_detail, ['product_id'], agg_dict)

prd['_prod_reorder_prob'] = prd._prod_buy_second_time_total_cnt / prd._prod_buy_first_time_total_cnt
prd['_prod_reorder_ratio'] = prd._prod_reorder_tot_cnts / prd._prod_tot_cnts
#prd['_prod_reorder_times'] = 1 + prd._prod_reorder_tot_cnts / prd._prod_buy_first_time_total_cnt
prd = prd.merge(products,on='product_id',how='left')
prd = prd.merge(departments,on='department_id',how='left')
prd = prd.merge(aisles,on='aisle_id',how='left')
del prd['department']
del prd['aisle']

print('product done')
print(time.ctime())
priors_orders_detail = priors_orders_detail.merge(prd,on='product_id',how='left')

"""
特征组2： 用户组，统计一些用户的信息
_user_total_orders: 用户的总订单数
_user_sum_days_since_prior_order: 距离上次购买时间(和),这个只能在orders表里面计算，priors_orders_detail不是在order level上面unique
_user_mean_days_since_prior_order: 距离上次购买时间(均值)
_user_std_days_since_prior_order：距离上次买的时间的标准差
_user_median_days_since_prior_order:距离上次买的时间的中位数
_dow,_hod：购买时间特征
# _user_reorder_ratio: reorder的总次数 / 第一单后买后的总次数
# _user_total_products: 用户购买的总商品数
# _user_distinct_products: 用户购买的unique商品数
_user_average_basket: 购物蓝的大小

"""
agg_dict_2 = {'order_number':{'_user_total_orders':'max'},
              'days_since_prior_order':{'_user_sum_days_since_prior_order':'sum', 
                                        '_user_mean_days_since_prior_order': 'mean',
                                        '_user_std_days_since_prior_order':'std'},
               'order_dow':{'_user_mean_dow':'mean',
                          '_user_std_dow':'std'},
              'order_hour_of_day':{'_user_mean_hod':'mean',
                                   '_user_std_hod':'std'}
               }
users = ka_add_groupby_features_1_vs_n(orders[orders.eval_set == 'prior'], ['user_id'], agg_dict_2)

#用户相关的特征重新写成以下格式，时间缩短为不到20秒

us = pd.concat([
    priors_orders_detail.groupby('user_id')['product_id'].count().rename('_user_total_products'),
    priors_orders_detail.groupby('user_id')['product_id'].nunique().rename('_user_distinct_products'),
    (priors_orders_detail.groupby('user_id')['reordered'].sum() /
        priors_orders_detail[priors_orders_detail['order_number'] > 1].groupby('user_id')['order_number'].count()).rename('_user_reorder_ratio')
], axis=1).reset_index()


users = users.merge(us, how='inner')
users['_user_average_basket'] = users._user_total_products / users._user_total_orders

us = orders[orders.eval_set != "prior"][['user_id', 'order_id', 'eval_set', 'days_since_prior_order']]
us.rename(index=str, columns={'days_since_prior_order': 'time_since_last_order'}, inplace=True)
users = users.merge(us, how='inner')
print('User Done')
print(time.ctime())
"""
0730： 加四个关于department和aisle的特征
从数据上看，department和aisle是类似于商品类别的数据，可能会非常有用。因此想知道：
这个department/aisle是否是用户最喜欢的？
这个department/aisle是否是用户最常订购的？
如果好用，可以再加最近订购的参数，类似一样的。
在最后的数据部分，由user_id和department_id/aisle_id一起join，也可以把这些作为一个特征输入进去。看看内存。
0731加入部门和aisle的recency特征
0801加入部门和aisle的dow/hour of day特征
"""
agg_dict_dept = {'user_id':{'_user_dept_total_orders':'count'},
              'reordered':{'_user_dept_total_reorders':'sum'},
              'days_since_prior_order':{'_user_dept_sum_days_since_prior_order':'sum', 
                                        '_user_dept_mean_days_since_prior_order': 'mean',
                                        '_user_dept_std_days_since_prior_order':'std'},
               'order_dow':{'_user_dpet_mean_dow':'mean',
                          '_user_dept_std_dow':'std'},
              'order_hour_of_day':{'_user_dept_mean_hod':'mean',
                                   '_user_dept_std_hod':'std'}
        }
agg_dict_ais = {'user_id':{'_user_ais_total_orders':'count'},
              'reordered':{'_user_ais_total_reorders':'sum'},
              'days_since_prior_order':{'_user_ais_sum_days_since_prior_order':'sum', 
                                        '_user_ais_mean_days_since_prior_order': 'mean',
                                        '_use_aisr_std_days_since_prior_order':'std'},
               'order_dow':{'_user_ais_mean_dow':'mean',
                          '_user_ais_std_dow':'std'},
              'order_hour_of_day':{'_user_ais_mean_hod':'mean',
                                   '_user_ais_std_hod':'std'}
        }

user_dept_data =  ka_add_groupby_features_1_vs_n(priors_orders_detail, 
                                                      group_columns_list=['user_id', 'department_id'], 
                                                      agg_dict=agg_dict_dept)
user_ais_data = ka_add_groupby_features_1_vs_n(priors_orders_detail, 
                                                      group_columns_list=['user_id', 'aisle_id'], 
                                                      agg_dict=agg_dict_ais)
user_dept_data['_user_dept_reorder_rate'] = user_dept_data['_user_dept_total_reorders']/user_dept_data['_user_dept_total_orders']
user_ais_data['_user_ais_reorder_rate'] = user_ais_data['_user_ais_total_reorders']/user_ais_data['_user_ais_total_orders']
print('User Ais Dept Done')
print(time.ctime())
"""
特征组3：用户和产品交互特征
0731： 加入：用户与产品的订购recency特征
"""

agg_dict_4 = {'order_number':{'_up_order_count': 'count', 
                              '_up_first_order_number': 'min', 
                              '_up_last_order_number':'max'}, 
              'add_to_cart_order':{'_up_average_cart_position': 'mean',
                                   '_up_cart_position_std':'std'},
              'order_dow':{'_user_prd_order_mean_day':'mean',
                           '_user_prd_order_std_day':'std'},
              'order_hour_of_day':{'_order_hod_mean':'mean',
                                   '_order_hod_std':'std'},
               'reordered':{'_total_time_of_reorder':'sum'},
               'days_since_prior_order':{'_user_prd_sum_days_since_prior_order':'sum', 
                                        '_user_prd_mean_days_since_prior_order': 'mean',
                                        '_use_prd_std_days_since_prior_order':'std'}}

data = ka_add_groupby_features_1_vs_n(df=priors_orders_detail, 
                                                      group_columns_list=['user_id', 'product_id'], 
                                                      agg_dict=agg_dict_4)

data = data.merge(prd, how='inner', on='product_id').merge(users, how='inner', on='user_id')
print('Data Done 1')
print(time.ctime())
# 该商品购买次数 / 总的订单数
# 最近一次购买商品 - 最后一次购买该商品
# 该商品购买次数 / 第一次购买该商品到最后一次购买商品的的订单数
data['_up_order_rate'] = data._up_order_count / data._user_total_orders
data['_up_order_since_last_order'] = data._user_total_orders - data._up_last_order_number
data['_up_order_rate_since_first_order'] = data._up_order_count / (data._user_total_orders - data._up_first_order_number + 1)
data['_usr_prd_reorder_rate'] = data._total_time_of_reorder/data._up_order_count
data['_usr_prd_buy_rate'] = data._up_order_count/data._user_total_products
# add user_id to train set
train = train.merge(right=orders[['order_id', 'user_id']], how='left', on='order_id')
data = data.merge(train[['user_id', 'product_id', 'reordered']], on=['user_id', 'product_id'], how='left')
data['reordered'] = data['reordered'].fillna(0)
data = data.merge(W2C,on='product_id',how='left')
data = data.merge(ostreak,on=['user_id','product_id'],how='left')
print('Data Done 2')
print(time.ctime())
data = data.merge(orders[['order_id','order_number','order_dow','order_hour_of_day','days_since_prior_order']],on='order_id',how='left')
del train, prd, users,priors_orders_detail, orders
del products,us,aisles,departments,priors,ostreak,W2C
del agg_dict,agg_dict_2,agg_dict_4,agg_dict_ais,agg_dict_dept

data = data.merge(user_dept_data,on=['user_id','department_id'],how='left')
del user_dept_data
data = data.merge(user_ais_data,on=['user_id','aisle_id'],how='left')
del user_ais_data
print('Data Done 3')
print(time.ctime())
#data = data.merge(dept,on='department_id',how='left').merge(ais,on='aisle_id',how='left')
#del dept,ais
#data = data.merge(product_name,on='product_id',how='left')
#del product_name
print('Data Done Final')
print(time.ctime())

train = data[data['eval_set']=='train']
test = data[data['eval_set']=='test']
del data,test
print('Ends')
print(time.ctime())

col = list(train.columns)

col.remove('reordered')
col.remove('eval_set')
col.remove('aisle_id')
col.remove('department_id')

from sklearn.model_selection import GroupKFold
kf = GroupKFold(n_splits=5) 
train_indexes = []
test_indexes = []
for i, (train_index, test_index) in enumerate(kf.split(train, groups=train['user_id'].values)):
    train_indexes.append(train_index)
    test_indexes.append(test_index)
train_index = train_indexes[0]
test_index = test_indexes[0]

training = train.iloc[train_index,:]
testing = train.iloc[test_index,:]
del train
del train_index,train_indexes,test_index,test_indexes
del i
from sklearn.metrics import roc_auc_score
from sklearn.metrics import log_loss

import lightgbm as lgb
dtrain = lgb.Dataset(training[col],training['reordered'])
validdata = lgb.Dataset(testing[col],testing['reordered'])
del training
lgb_params = {
    'learning_rate': 0.1,
    'boosting_type': 'gbdt',
    'objective': 'binary',
    'metric': {'binary_logloss'},
    'num_leaves': 240,
    'feature_fraction': 0.95,
    'bagging_fraction': 0.76,
    'bagging_freq': 5,
    'max_bin':500
     }
print('Start training')
model = lgb.train(lgb_params, dtrain, 2000,verbose_eval=30,early_stopping_rounds = 25,valid_sets=[dtrain, validdata])
print('Start predicting')
pred = model.predict(testing[col],num_iteration=model.best_iteration)
print('Prediction Done')
actual_pred = [1 if each>=0.5 else 0 for each in pred]
print(roc_auc_score(actual_pred,testing['reordered']))
print(log_loss(actual_pred,testing['reordered']))
FScore=Cross_Validation(testing,pred,0.2) 
print(FScore)
FI = get_feature_importance_lgb(model)
FI.to_csv('FI_wo_median_with_original_orderinfo.csv',index=False)

'''
Start training
Train until valid scores didn't improve in 25 rounds.
[30]    training's binary_logloss: 0.249765     valid_1's binary_logloss: 0.250451
[60]    training's binary_logloss: 0.24146      valid_1's binary_logloss: 0.243921
[90]    training's binary_logloss: 0.23899      valid_1's binary_logloss: 0.243577
[120]   training's binary_logloss: 0.237014     valid_1's binary_logloss: 0.243589
Early stopping, best iteration is:
[113]   training's binary_logloss: 0.237436     valid_1's binary_logloss: 0.243565
Start predicting
Prediction Done
0.780376570833
3.08385578121
0.382306666956
'''


evals = []
for leave in [80,120,300,500,1000]:
    lgb_params = {'learning_rate': 0.1,
                      'boosting_type': 'gbdt',
                      'objective': 'binary',
                      'metric': {'binary_logloss'},
                      'num_leaves': leave,
                      'feature_fraction': 0.95,
                      'bagging_fraction': 0.76,
                      'bagging_freq': 5,
                      'max_bin':500}
    print('Start training')
    model = lgb.train(lgb_params, dtrain, 2000,verbose_eval=30,early_stopping_rounds = 25,valid_sets=[dtrain, validdata])
    print('Start predicting')
    pred = model.predict(testing[col],num_iteration=model.best_iteration)
    print('Prediction Done')
    actual_pred = [1 if each>=0.5 else 0 for each in pred]
    AUC=roc_auc_score(actual_pred,testing['reordered'])
    LL=log_loss(actual_pred,testing['reordered'])
    FScore=Cross_Validation(testing,pred,0.2) 
    report = {'Leave':leave,'Rounds':model.best_iteration,'AUC':AUC,'logloss':LL,'FScore':FScore}
    evals.append(report)
    print(str(report))


"""
{'Leave': 80, 'Rounds': 156, 'AUC': 0.78004792795379296, 'logloss': 3.0868106539290761, 'FScore': 0.38220230012299128}
{'Leave': 120, 'Rounds': 128, 'AUC': 0.78020761898833768, 'logloss': 3.0845078735574276, 'FScore': 0.38278188372018074}
{'Leave': 300, 'Rounds': 86, 'AUC': 0.78024088970033223, 'logloss': 3.0854249274394698, 'FScore': 0.38236093882403738}
{'Leave': 500, 'Rounds': 83, 'AUC': 0.7806224606790827, 'logloss': 3.0830202931825288, 'FScore': 0.3818875921372763}
{'Leave': 1000, 'Rounds': 62, 'AUC': 0.77919375625221488, 'logloss': 3.0889298989803216, 'FScore': 0.38136065352170423}
"""

evals = []
for leave in [100,150,180,200,220]:
    lgb_params = {'learning_rate': 0.1,
                      'boosting_type': 'gbdt',
                      'objective': 'binary',
                      'metric': {'binary_logloss'},
                      'num_leaves': leave,
                      'feature_fraction': 0.95,
                      'bagging_fraction': 0.76,
                      'bagging_freq': 5,
                      'max_bin':500}
    print('Start training')
    model = lgb.train(lgb_params, dtrain, 2000,verbose_eval=30,early_stopping_rounds = 25,valid_sets=[dtrain, validdata])
    print('Start predicting')
    pred = model.predict(testing[col],num_iteration=model.best_iteration)
    print('Prediction Done')
    actual_pred = [1 if each>=0.5 else 0 for each in pred]
    AUC=roc_auc_score(actual_pred,testing['reordered'])
    LL=log_loss(actual_pred,testing['reordered'])
    FScore=Cross_Validation(testing,pred,0.2) 
    report = {'Leave':leave,'Rounds':model.best_iteration,'AUC':AUC,'logloss':LL,'FScore':FScore}
    evals.append(report)
    print(str(report))


"""
{'Leave': 100, 'Rounds': 155, 'AUC': 0.7805152668344425, 'logloss': 3.0838558062132142, 'FScore': 0.38269321519282784}
{'Leave': 150, 'Rounds': 124, 'AUC': 0.78090489866430812, 'logloss': 3.0827961766112262, 'FScore': 0.3826180452309581}
{'Leave': 180, 'Rounds': 122, 'AUC': 0.78034577128310345, 'logloss': 3.0843448678076761, 'FScore': 0.38272281636202771}
{'Leave': 200, 'Rounds': 106, 'AUC': 0.78073142074770596, 'logloss': 3.0829999339163541, 'FScore': 0.38237134262051703}
{'Leave': 220, 'Rounds': 102, 'AUC': 0.78033586941499344, 'logloss': 3.0848339581793516, 'FScore': 0.38197449777961928}
"""
lgb_params = {
    'learning_rate': 0.01,
    'boosting_type': 'gbdt',
    'objective': 'binary',
    'metric': {'binary_logloss'},
    'num_leaves': 120,
    'feature_fraction': 0.95,
    'bagging_fraction': 0.76,
    'bagging_freq': 5,
    'max_bin':500
     }
print('Start training')
model = lgb.train(lgb_params, dtrain, 3000,verbose_eval=30,early_stopping_rounds = 25,valid_sets=[dtrain, validdata])
print('Start predicting')
pred = model.predict(testing[col],num_iteration=model.best_iteration)
print('Prediction Done')
actual_pred = [1 if each>=0.5 else 0 for each in pred]
print(roc_auc_score(actual_pred,testing['reordered']))
print(log_loss(actual_pred,testing['reordered']))
FScore=Cross_Validation(testing,pred,0.2) 
print(FScore)

"""
Early stopping, best iteration is:
[1792]  training's binary_logloss: 0.238165     valid_1's binary_logloss: 0.243191
Start predicting
Prediction Done
0.781131543851
3.08330568758
0.383408382211

"""
