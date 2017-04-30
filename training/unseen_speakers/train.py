from keras.optimizers import Adam
from keras.callbacks import TensorBoard, CSVLogger, ModelCheckpoint
from lipnet.lipreading.generators import BasicGenerator
from lipnet.lipreading.callbacks import Statistics, Visualize
from lipnet.model import LipNet
import numpy as np
import datetime
import os

np.random.seed(55)

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR  = os.path.join(CURRENT_PATH, 'datasets')
OUTPUT_DIR   = os.path.join(CURRENT_PATH, 'results')
LOG_DIR      = os.path.join(CURRENT_PATH, 'logs')

def train(run_name, start_epoch, stop_epoch, img_c, img_w, img_h, frames_n, absolute_max_string_len, minibatch_size):
    lip_gen = BasicGenerator(dataset_path=DATASET_DIR, 
                                minibatch_size=minibatch_size,
                                img_c=img_c, img_w=img_w, img_h=img_h, frames_n=frames_n,
                                absolute_max_string_len=absolute_max_string_len).build()

    lipnet = LipNet(img_c=img_c, img_w=img_w, img_h=img_h, frames_n=frames_n, 
                            absolute_max_string_len=absolute_max_string_len, output_size=lip_gen.get_output_size())
    lipnet.summary()

    adam = Adam(lr=0.0001, beta_1=0.9, beta_2=0.999, epsilon=1e-08)

    # the loss calc occurs elsewhere, so use a dummy lambda func for the loss
    lipnet.model.compile(loss={'ctc': lambda y_true, y_pred: y_pred}, optimizer=adam)

    # load weight if necessary
    if start_epoch > 0:
        weight_file = os.path.join(OUTPUT_DIR, os.path.join(run_name, 'weights%02d.h5' % (start_epoch - 1)))
        lipnet.model.load_weights(weight_file)

    # define callbacks
    statistics  = Statistics(lipnet.test_function, lip_gen.next_val(), 256, output_dir=os.path.join(OUTPUT_DIR, run_name))
    visualize   = Visualize(os.path.join(OUTPUT_DIR, run_name), lipnet.test_function, lip_gen.next_val(), minibatch_size)
    tensorboard = TensorBoard(log_dir=os.path.join(LOG_DIR, run_name))
    csv_logger  = CSVLogger(os.path.join(LOG_DIR, "{}-{}.csv".format('training',run_name)), separator=',', append=False)
    checkpoint  = ModelCheckpoint(os.path.join(OUTPUT_DIR, run_name, "weights.{epoch:02d}-{val_loss:.2f}.h5"), monitor='val_loss', save_weights_only=True, mode='auto', period=1)

    lipnet.model.fit_generator(generator=lip_gen.next_train(), 
                        steps_per_epoch=lip_gen.training_size, epochs=stop_epoch, 
                        validation_data=lip_gen.next_val(), validation_steps=lip_gen.validation_size,
                        callbacks=[checkpoint, statistics, visualize, lip_gen, tensorboard, csv_logger], 
                        initial_epoch=start_epoch, 
                        verbose=1,
                        max_q_size=10,
                        workers=8,
                        pickle_safe=True)

if __name__ == '__main__':
    run_name = datetime.datetime.now().strftime('%Y:%m:%d:%H:%M:%S')
    train(run_name, 0, 20, 3, 100, 50, 75, 32, 50)