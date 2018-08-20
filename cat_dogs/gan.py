"""
# author: shiyipaisizuo
# contact: shiyipaisizuo@gmail.com
# file: gan.py
# time: 2018/8/10 07:27
# license: MIT
"""

import os
import time

import torch
import torchvision
from torch import nn
from torchvision import transforms
from torchvision.utils import save_image

# Device configuration
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Setting hyper-parameters
parser = argparse.ArgumentParser()
parser.add_argument('--path_dir', type=str, default='../data/catdog/',
                    help="""input image path dir.Default: '../data/catdog/'.""")
parser.add_argument('--external_dir', type=str, default='../data/catdog/external_data/',
                    help="""input image path dir.Default: '../data/catdog/external_data/'.""")
parser.add_argument('--latent_size', type=int, default=64,
                    help="""Latent_size. Default: 64.""")
parser.add_argument('--hidden_size', type=int, default=1024,
                    help="""Hidden size. Default: 1024.""")
parser.add_argument('--batch_size', type=int, default=64,
                    help="""Batch size. Default: 64.""")
parser.add_argument('--image_size', type=int, default=28 * 28 * 3,
                    help="""Input image size. Default: 28 * 28 * 3.""")
parser.add_argument('--max_epochs', type=int, default=100,
                    help="""Max epoch. Default: 100.""")
parser.add_argument('--display_epoch', type=int, default=5,
                    help="""When epochs save image. Default: 5.""")
args = parser.parse_args()

# Create a directory if not exists
if not os.path.exists(args.external_dir):
    os.makedirs(args.external_dir)

# Image processing
transform = transforms.Compose([
    transforms.Resize(28),
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.5, 0.5, 0.5),  std=(0.5, 0.5, 0.5))])  # # 3 for RGB channels

# MNIST dataset
mnist = torchvision.datasets.MNIST(root='../data/mnist',
                                   train=True,
                                   transform=transform,
                                   download=True)

# Data loader
data_loader = torch.utils.data.DataLoader(dataset=mnist,
                                          batch_size=batch_size,
                                          shuffle=True)

# Discriminator
D = nn.Sequential(
    nn.Linear(image_size, hidden_size),
    nn.LeakyReLU(0.2),
    nn.Linear(hidden_size, hidden_size),
    nn.LeakyReLU(0.2),
    nn.Linear(hidden_size, 1),
    nn.Sigmoid())

# Generator
G = nn.Sequential(
    nn.Linear(latent_size, hidden_size),
    nn.ReLU(),
    nn.Linear(hidden_size, hidden_size),
    nn.ReLU(),
    nn.Linear(hidden_size, image_size),
    nn.Tanh())

# Device setting
D = torch.load('D.ckpt').to(device)
G = torch.load('G.ckpt').to(device)

# Binary cross entropy loss and optimizer
criterion = nn.BCEWithLogitsLoss().to(device)
d_optimizer = torch.optim.Adam(D.parameters(), lr=0.0001, weight_decay=1e-5)
g_optimizer = torch.optim.Adam(G.parameters(), lr=0.0001, weight_decay=1e-5)


def denorm(x):
    out = (x + 1) / 2
    return out.clamp(0, 1)


def reset_grad():
    d_optimizer.zero_grad()
    g_optimizer.zero_grad()


# Start training
total_step = len(data_loader)
for epoch in range(num_epochs):
    for i, (images, _) in enumerate(data_loader):
        images = images.reshape(batch_size, -1).to(device)

        # Create the labels which are later used as input for the BCE loss
        real_labels = torch.ones(batch_size, 1).to(device)
        fake_labels = torch.zeros(batch_size, 1).to(device)

        # ================================================================== #
        #                      Train the discriminator                       #
        # ================================================================== #

        # Compute BCE_Loss using real images where BCE_Loss(x, y): - y * log(D(x)) - (1-y) * log(1 - D(x))
        # Second term of the loss is always zero since real_labels == 1
        outputs = D(images)
        d_loss_real = criterion(outputs, real_labels)
        real_score = outputs

        # Compute BCELoss using fake images
        # First term of the loss is always zero since fake_labels == 0
        z = torch.randn(batch_size, latent_size).to(device)
        fake_images = G(z)
        outputs = D(fake_images)
        d_loss_fake = criterion(outputs, fake_labels)
        fake_score = outputs

        # Backprop and optimize
        d_loss = d_loss_real + d_loss_fake
        reset_grad()
        d_loss.backward()
        d_optimizer.step()

        # ================================================================== #
        #                        Train the generator                         #
        # ================================================================== #

        # Compute loss with fake images
        z = torch.randn(batch_size, latent_size).to(device)
        fake_images = G(z)
        outputs = D(fake_images)

        # We train G to maximize log(D(G(z)) instead of minimizing log(1-D(G(z)))
        # For the reason, see the last paragraph of section 3. https://arxiv.org/pdf/1406.2661.pdf
        g_loss = criterion(outputs, real_labels)

        # Backprop and optimize
        reset_grad()
        g_loss.backward()
        g_optimizer.step()

        if (i + 1) % 200 == 0:
            print('Epoch [{}/{}], Step [{}/{}], d_loss: {:.4f}, g_loss: {:.4f}, D(x): {:.2f}, D(G(z)): {:.2f}'
                  .format(epoch, num_epochs, i + 1, total_step, d_loss.item(), g_loss.item(),
                          real_score.mean().item(), fake_score.mean().item()))

    # Save real images
    if (epoch + 1) == 1:
        images = images.reshape(images.size(0), 1, 28, 28)
        save_image(denorm(images), os.path.join(sample_dir, 'real_images.jpg'))

    # Save sampled images
    fake_images = fake_images.reshape(fake_images.size(0), 1, 28, 28)
    save_image(denorm(fake_images), os.path.join(sample_dir, 'fake_images-{}.jpg'.format(epoch + 1)))

# Save the model checkpoints
torch.save(G, 'G.ckpt')
torch.save(D, 'D.ckpt')
