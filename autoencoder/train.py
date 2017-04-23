# Copyright 2016 Goekcen Eraslan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os, json

from . import io

import numpy as np
import keras.optimizers as opt
from keras.callbacks import TensorBoard, ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from keras import backend as K


def train(X, model, loss, optimizer='Adam', learning_rate=None, train_on_full=False,
          log_dir='logs', aetype=None, epochs=200, reduce_lr_epoch=20,
          early_stopping_epoch=25, batch_size=32,
          hyperpar=None, **kwargs):

    if learning_rate is None:
        optimizer = opt.__dict__[optimizer]()
    else:
        optimizer = opt.__dict__[optimizer](learning_rate=learning_rate)

    model.compile(loss=loss, optimizer=optimizer)

    # Callbacks
    checkpointer = ModelCheckpoint(filepath="%s/weights.{epoch:02d}-{val_loss:.4f}.hdf5" % log_dir,
                                   verbose=1,
                                   save_weights_only=True,
                                   save_best_only=True)
    es_cb = EarlyStopping(monitor='val_loss', patience=early_stopping_epoch)
    es_cb_train = EarlyStopping(monitor='train_loss', patience=early_stopping_epoch)

    lr_cb = ReduceLROnPlateau(monitor='val_loss', patience=reduce_lr_epoch)
    lr_cb_train = ReduceLROnPlateau(monitor='train_loss', patience=reduce_lr_epoch)

    callbacks = [checkpointer]
    callbacks_train = [checkpointer]

    if reduce_lr_epoch:
        callbacks.append(lr_cb)
        callbacks_train.append(lr_cb_train)
    if early_stopping_epoch:
        callbacks.append(es_cb)
        callbacks_train.append(es_cb_train)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    with open('%s/arch.json' % log_dir, 'w') as f:
        json.dump(model.to_json(), f)

    print(model.summary())

    fold_losses = list()
    for i, data in enumerate(X['folds']):
        tb_log_dir = os.path.join(log_dir, 'fold%0i' % i)
        tb_cb = TensorBoard(log_dir=tb_log_dir, histogram_freq=1)

        loss = model.fit(data['train'], data['train'],
                         epochs=epochs,
                         batch_size=batch_size,
                         shuffle=True,
                         callbacks=callbacks+[tb_cb],
                         validation_data=(data['val'], data['val']),
                         **kwargs)
        #model.evaluate(data['test'], data['test'], batch_size=32,
        #               verbose=1, sample_weight=None)
        fold_losses.append(loss.history)

    ret =  {'fold': fold_losses}

    if train_on_full:
        # run final training on full dataset
        full_data = np.concatenate((X['folds'][0]['train'],
                                    X['folds'][0]['val']))
        if 'test' in X['folds'][0]:
            full_data = np.concatenate((full_data, X['folds'][0]['test']))

        tb_log_dir = os.path.join(log_dir, 'full')
        tb_cb = TensorBoard(log_dir=tb_log_dir, histogram_freq=1)

        loss = model.fit(full_data, full_data,
                         epochs=epochs,
                         batch_size=batch_size,
                         shuffle=True,
                         callbacks=callbacks_train+[tb_cb],
                         **kwargs)
        ret['full'] = loss.history

    #https://github.com/tensorflow/tensorflow/issues/3388
    #K.clear_session()

    return ret


def train_with_args(args):
    X = io.read_from_file(args.trainingset)

    train(X=X, hidden_size=args.hiddensize,
          learning_rate=args.learningrate,
          log_dir=args.logdir,
          aetype=args.type,
          epochs=args.epochs,
          hyperpar=args.hyperpar)
