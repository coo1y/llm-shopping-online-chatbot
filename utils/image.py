from PIL import Image

def resize_image(image_file, size=(600, 720)):
    image = Image.open(image_file)
    new_image = image.resize(size)

    return new_image

