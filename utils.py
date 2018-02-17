#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 09:26:37 2018

@author: dhingratul
"""
import pandas as pd
from sklearn import preprocessing
import numpy as np


def oneHot(df, y, clip=True, thresh=False):
    """
    Helper function to one-hot encode a vector
    Input: {df, y, clip, thresh}
    -- df =  Input Dataframe used for getting shape of input(number of data points), 
    -- y = Encoded labels b/w 0 to num_classes, of feature column(see getEncoded()),
    -- clip = Clips the number of features to be less than a threshold(thresh)
    -- thresh = {thresh = False; thresholds at mean value, 
                          integer value} 
    
    Output: {x} 
    -- x = One-hot encoded vector
    
    Note: Please use from within getEncoded()
    """
    n = y.max() + 1
    m = df.shape[0]
    oh = np.zeros((m, n))
    for i in range(m):
        oh[i][y[i]] = 1 
    if clip is True:
        sum_ = oh.sum(axis=0)
        frac = sum_ / float(sum(sum_))
        if thresh is False:
            x = oh[:,frac > frac.mean()]
        else:
            x = oh[:,frac > thresh]
    else:
        x = oh
    return x


def getEncoded(df, feat, column, out_name, oh=False, clip=False, write_out=False):
    """
    Helper function to one-hot encode a vector
    Input: {df, feat, column, out_name, oh, clip, write_out}
    -- df =  Input Dataframe 
    -- feat = List to store one hot features generated,
    -- column = Column name of feature in df
    -- out_name = name of column for the resulting data to be stored in df based on write_out
    -- oh = Boolean, set it True to obtain one-hot encoded vectors, calls oneHot()
    -- clip = Clips the number of features to be less than a threshold(thresh) see oneHot() for details
    -- write_out = Boolean, set to True, if you want the resulting feature to be stored in the df inplace
    
    Output: {df, feat, le} 
    -- df =  Input Dataframe with features written inplace for write_out=True
    -- feat = Returns a list with appended feature generated    
    -- le = Label encoder used for converting the unique values in range 0 to num_classes - 1
    """
    le = preprocessing.LabelEncoder()
    le.fit(df[column])
    y = le.transform(df[column]) 
    if write_out is True:
        df[out_name] = pd.Series(y)
    # One Hot encode features
    if oh is True:
        x = oneHot(df, y, clip, thresh=False)
        feat.append(x)
    return df, feat, le



def randomSample(train, num_samples):
    """
    Helper function to sample random negative(-1 class) data points
    Input: {train, num_samples}
    -- train = Dataframe with only -1 labels
    -- num_samples = Number of data points to be sampled 
    
    Output: {df} 
    -- df =  (num_samples number of) randomly sampled datapoints as a dataframe

    Note: Please use from within split_training_testing()
    """
    fraud = train[train['y'] == 1]
    n_fraud = train[train['y'] == 0].sample(n = num_samples, random_state=0)
    df = pd.concat([fraud, n_fraud], ignore_index=True)
    df = df.sample(frac=1, random_state=0).reset_index(drop=True)
    return df


def split_training_testing(X, Y, gnd, negative=10000, per=0.05):
    """
    Helper function to split data into training and testing set
    Input: {X, Y, gnd, negative, per}
    -- X = Feature matrice: Input features generated by stacking getEncoded() output on multiple features
    -- Y = Labels of corresponding X matrix
    -- gnd = Class labels of all data points in X from LabelEncoder()
    -- negative = Int, Number of negative class samples to be sampled
    -- per = Percentage of +1 samples in testing set among all +1 samples. 
    
    Output: {X_train, y_train, gnd_tr, X_test, y_test, gnd_te} 
    -- X_train =  Training set
    -- y_train = training labels -- +1 for fraud data points, 0 for others    
    -- gnd_tr = Class labels for samples in training set generated from LabelEncoder()
    -- X_test = Testing set
    -- y_test = Testing labels -- +1, Only contains fraud data points
    -- gnd_te = Class labels for samples in testing set generated from LabelEncoder()
    
    Note: There are only +1 samples in testing set, this is the only way to
    judge model accuracy without ground truth -1 labels
    """
    df_x = pd.DataFrame(X)
    df_x['y'] = Y
    df_x['gnd'] = gnd
    df_x.sort_values(by=['y'], inplace=True, ascending=False)
    frac_positive = (df_x[df_x['y'] == 1].shape[0])/float(df_x.shape[0])
    split = int(frac_positive * per * df_x.shape[0])
    df_x.reset_index(drop=True, inplace=True)
    test = df_x.iloc[:split]
    train = df_x.iloc[split:]
    train = randomSample(train, negative)
    y_train = train['y'].as_matrix()
    y_train_gnd = train['gnd'].as_matrix()
    train = train.drop(['y'], axis=1)
    train = train.drop(['gnd'], axis=1)
    
    y_test = test['y'].as_matrix()
    y_test_gnd = test['gnd'].as_matrix()
    test.drop(['y'], axis=1, inplace=True)
    test.drop(['gnd'], axis=1, inplace=True)
    return train.as_matrix(), y_train, y_train_gnd, test.as_matrix(), y_test, y_test_gnd


def voting(y_pred_test, gnd_te):
    """
    Helper function to judge the accuracy of model on test set
    Input: {y_pred_test, gnd_te}
    -- y_pred_test = Prediction of model on y_test 
    -- gnd_te = Class labels for samples in testing set generated from LabelEncoder()

    Output: {acc_vot} 
    -- acc_vot =  Model Accuracy on Test Set
    """
    df = pd.DataFrame({'y':y_pred_test, 'gnd':gnd_te})
    df.sort_values(by=['y'], inplace=True, ascending=False)
    out = df.groupby(['gnd']).mean()
    return len(out[out['y'] > 0])/float(len(out))


def evaluate(y_pred_X, gnd, thresh, le_y):
    """
    Helper function to evaluate the model on input data to produce fraud list
    Input: {y_pred_X, gnd, thresh, le_y}
    -- y_pred_X = Prediction of model on X 
    -- gnd = Class labels for samples in X generated from LabelEncoder()
    -- thresh = threshold for majority voting over which samples are treated as fraud
    -- le_y = Label encoder used for converting 'y' in range 0 to num_classes - 1 
    
    Output: {fraud_list} 
    -- fraud_list =  List of fraud urls 
    """
    df2 = pd.DataFrame({'y':y_pred_X, 'gnd':gnd})
    #df.sort_values(by=['y'], inplace=True, ascending=False) 
    out = df2.groupby(['gnd']).mean()
    out.reset_index(inplace=True)
    labels = out['gnd'].as_matrix()
    mask2 = labels[out['y'] > thresh]
    return list(le_y.inverse_transform(mask2))


def encodeDates(df, feat, column, freq='5min'):
    """
    Helper function to convert timestamps from data into buckets of frequency freq
    Input: {df, feat, column, freq}
    -- df =  Input Dataframe 
    -- feat = List to store one hot features generated,
    -- column = Name of feature in df
    -- freq = Frequency with which to segment the data into "freq" long periods
    
    Output: {feat} 
    -- feat = Returns a list with appended feature generated    
    """
    y = pd.date_range(df[column].min(), df[column].max(), freq=freq)
    out = np.zeros((df.shape[0], len(y) - 1))
    for j in range(1, len(y) - 1):
        x=df[(df[column] < y[j]) & (df[column] >= y[j - 1])]
        out[x.index[0]:x.index[-1], j-1] = 1
    feat.append(out)
    return feat
