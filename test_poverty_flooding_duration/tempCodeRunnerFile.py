    import matplotlib.pyplot as plt

    # Visualize the pop_masked image
    vis_params = {
        'min': 0,
        'max': 1000,
        'palette': ['000000', 'FF0000']
    }

    pop_masked_vis = pop_masked.visualize(**vis_params)

    # Convert the image to a numpy array
    pop_masked_array = pop_masked_vis.toArray().getInfo()

    # Plot the numpy array using matplotlib
    plt.imshow(pop_masked_array, cmap='gray')
    plt.colorbar()
    plt.title('Flooded Population')
    plt.show()