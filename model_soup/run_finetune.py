# @Time   : 2020/10/6
# @Author : Shanlei Mu
# @Email  : slmu@ruc.edu.cn

"""
recbole.quick_start
########################
"""
import torch

import logging
from logging import getLogger

from recbole.config import Config
from recbole.data import create_dataset, data_preparation
from recbole.utils import init_logger, get_model, get_trainer, init_seed
from recbole.utils.utils import set_color

import wandb




def run_finetune(model=None, dataset=None, config_file_list=None, config_dict=None, saved=True):
    r""" A fast running api, which includes the complete process of
    training and testing a model on a specified dataset

    Args:
        model (str): model name
        dataset (str): dataset name
        config_file_list (list): config files used to modify experiment parameters
        config_dict (dict): parameters dictionary used to modify experiment parameters
        saved (bool): whether to save the model
    """
    # configurations initialization
    config = Config(model=model, dataset=dataset, config_file_list=config_file_list, config_dict=config_dict)
    config['model'] = 'BasicRec'
    config['log_root'] = './log/FINETUNE/'
    config['epochs'] = 20
    
    wandb.init(project='FineTuneRec', name='baseline', config=config) #, mode='disabled')
    # init_seed(config['seed'], config['reproducibility'])

    # logger initialization
    init_logger(config)
    logger = getLogger()

    import os
    # log_dir = os.path.dirname(logger.handlers[0].baseFilename)
    log_dir = 'log/FINETUNE/BasicRec/ml-1m/bs256-lmd0.1-sem0.1-us_x-May-27-2023_18-07-14-lr0.001-l20-tau1-dot-DPh0.5-DPa0.5'
    config['log_dir'] = log_dir
    print('log dir :', log_dir)

    wandb.config.update({'log_dir':log_dir})
    
    logger.info(config)

    # # dataset filtering
    # dataset = create_dataset(config)
    # logger.info(dataset)

    # # dataset splitting
    # train_data, valid_data, test_data = data_preparation(config, dataset)

    # # model loading and initialization
    # model = get_model(config['model'])(config, train_data).to(config['device'])
    # logger.info(model)
    
    # # trainer loading and initialization
    # trainer = get_trainer(config['MODEL_TYPE'], config['model'])(config, model)
    
    # os.makedirs(os.path.join(config['log_dir'], config['model']))
    
    # # model training
    # best_valid_score, best_valid_result = trainer.fit(
    #     train_data, valid_data, saved=saved, show_progress=config['show_progress']
    # )
    # trainer.saved_model_file = os.path.join(config['log_dir'], 'basic_model.pth')
    # trainer._save_checkpoint(epoch=config['epochs'])

    ################################################
    #    BasicRec | CL4SRec, DuoRec, AdaptiveRec    #    
    ################################################
    
    for model_name in ['CL4SRec', 'DuoRec', 'AdaptiveRec']:
        print('*'*20, model_name, '*'*20)
        config['model'] = model_name; config['SSL_AUG'] = model_name
        config['learning_rate'] = 1e-4
        config['epochs'] += 30

        
        ###
        wandb.init(project='FineTuneRec', name=config['model'], config=config) #, mode='disabled')
        
        dataset = create_dataset(config)
        train_data, valid_data, test_data = data_preparation(config, dataset)
        
        model = get_model(config['model'])(config, train_data).to(config['device'])
        
        # trainer loading and initialization to final(best) parameter of BasicRec
        finetune_trainer = get_trainer(config['MODEL_TYPE'], config['model'])(config, model)
        if model_name == 'CL4SRec':
            padded_ = torch.load(os.path.join(config['log_dir'], 'basic_model.pth'), map_location=finetune_trainer.device)
            
            layer_ = 'item_embedding.weight'
            layer_param = padded_['state_dict'][layer_]
            padded_['state_dict'][layer_] =  torch.concat((layer_param, torch.zeros(1,layer_param.shape[1]).to(finetune_trainer.device)), 0)
            
            finetune_trainer.model.load_state_dict(padded_['state_dict'])
            finetune_trainer.saved_model_file = os.path.join(config['log_dir'], f'{model_name}_model.pth')
        else:
            finetune_trainer.resume_checkpoint(resume_file=os.path.join(config['log_dir'], 'basic_model.pth'))
        
        os.makedirs(os.path.join(config['log_dir'], config['model']), exist_ok=True)
        finetune_trainer.saved_model_file = os.path.join(config['log_dir'], f'{model_name}_model.pth')
        finetune_trainer._save_checkpoint(epoch=-1)
        
        # model training
        best_valid_score, best_valid_result = finetune_trainer.fit(
            train_data, valid_data, saved=saved, show_progress=config['show_progress']
        )
        finetune_trainer.saved_model_file = os.path.join(config['log_dir'], f'{model_name}_model.pth')
        finetune_trainer._save_checkpoint(epoch=config['epochs'])
        
        print(config['eval_setting'],'-----------')
        test_result = finetune_trainer.evaluate(eval_data=test_data, load_best_model=True, show_progress=config['show_progress'])
        # logger.info(set_color('test result', 'yellow') + f': {test_result}')
        print(test_result)
        
        wandb.log({'test_result':test_result})
        
        del finetune_trainer, test_result


        # random setting (uni100)
        if config['eval_uniform_setting'] == True:
            config['eval_setting'] = 'TO_LS,uni100' 
            dataset = create_dataset(config)
            train_data, valid_data, test_data = data_preparation(config, dataset)
            
            model = get_model(config['model'])(config, train_data).to(config['device'])
            trainer = get_trainer(config['MODEL_TYPE'], config['model'])(config, model)
            trainer.resume_checkpoint(resume_file=os.path.join(config['log_dir'], f'{model_name}_model.pth'))
            
            print(config['eval_setting'],'-----------')
            test_random_result = trainer.evaluate(test_data, load_best_model=False, show_progress=config['show_progress'])
            
            # logger.info(set_color('test random result', 'yellow') + f': {test_random_result}')
            print(test_random_result)
            wandb.log({'test_random_result':test_random_result})



        # popular setting (pop100)
        if config['eval_popular_setting'] == True:
            config['eval_setting'] = 'TO_LS,pop100' 
            dataset = create_dataset(config)
            train_data, valid_data, test_data = data_preparation(config, dataset)
            
            model = get_model(config['model'])(config, train_data).to(config['device'])
            trainer = get_trainer(config['MODEL_TYPE'], config['model'])(config, model)
            trainer.resume_checkpoint(resume_file=os.path.join(config['log_dir'], f'{model_name}_model.pth'))
            
            print(config['eval_setting'],'-----------')
            test_popular_result = trainer.evaluate(test_data, load_best_model=False, show_progress=config['show_progress'])
            
            # logger.info(set_color('test popular result', 'yellow') + f': {test_popular_result}')
            print(test_popular_result)
            wandb.log({'test_popular_result':test_popular_result})
    




def objective_function(config_dict=None, config_file_list=None, saved=True):
    r""" The default objective_function used in HyperTuning

    Args:
        config_dict (dict): parameters dictionary used to modify experiment parameters
        config_file_list (list): config files used to modify experiment parameters
        saved (bool): whether to save the model
    """

    config = Config(config_dict=config_dict, config_file_list=config_file_list)
    init_seed(config['seed'], config['reproducibility'])
    logging.basicConfig(level=logging.ERROR)
    dataset = create_dataset(config)
    train_data, valid_data, test_data = data_preparation(config, dataset)
    model = get_model(config['model'])(config, train_data).to(config['device'])
    trainer = get_trainer(config['MODEL_TYPE'], config['model'])(config, model)
    best_valid_score, best_valid_result = trainer.fit(train_data, valid_data, verbose=False, saved=saved)
    test_result = trainer.evaluate(test_data, load_best_model=saved)

    return {
        'best_valid_score': best_valid_score,
        'valid_score_bigger': config['valid_metric_bigger'],
        'best_valid_result': best_valid_result,
        'test_result': test_result
    }
