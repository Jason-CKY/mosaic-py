from PIL import Image
import os
import random
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('--large_image_path', type=str, default='Reference.jpg', help='path to the large image')
    parser.add_argument('--small_image_folder', type=str, default='../data/cats/', help='path to the small images folder(folder should contain between 400-1,000 images for best results')
    parser.add_argument('--final_size', type=int, default=2000, help='target height of final image (pixel values between 1,000-20,000 for best results)')
    parser.add_argument('--small_image_size', type=int, default=100, help='size of small images (pixel values between 50-200 for best results)')
    
    return parser.parse_args()

def resize_crop(image, size):   
    crop_size = 0
    if image.size[0] > image.size[1]:
        crop_size = image.size[1]
    else:
        crop_size = image.size[0]
    image = image.crop((0,0,crop_size,crop_size))
    image.thumbnail((size, size), Image.ANTIALIAS)
    return image

def scale_large_image(image: Image, size, small_image_size):   
    '''
    size: size of one edge of the photo. short edge if not perfect square.
    '''
    aspect_ratio = image.size[0] / image.size[1]
    short_edge = image.size[1] if image.size[0] > image.size[1] else image.size[0]
    long_edge = image.size[0] if image.size[0] > image.size[1] else image.size[1]
    aspect_ratio = long_edge / short_edge

    final_long_edge = int(size * aspect_ratio)
    
    print(long_edge, small_image_size, final_long_edge)
    if final_long_edge % small_image_size != 0:
        final_long_edge -= (final_long_edge % small_image_size)
    

    assert final_long_edge % small_image_size == 0

    if image.size[0] > image.size[1]:
        final_size = (final_long_edge, size)
    else:
        final_size = (size, final_long_edge)

    # image = image.crop((0,0,crop_size,crop_size))
    image = image.resize(final_size)
    image.thumbnail(final_size, Image.ANTIALIAS)
    return image

def get_target_pixels(image):   
    width, height = image.size
    large_image_pixels = []
    for x in range(0, width):
        for y in range(0, height):
            r, g, b = image.getpixel((x,y))
            average = int((r+g+b)/3)
            large_image_pixels.append(average)
    return large_image_pixels
            
def get_small_averages(path, small_image_size):
    image_list = []
    image_brightness_list = []

    for file in os.listdir(path):
        small_image = Image.open("{}/{}".format(path,file))
        resized_small_image = resize_crop(small_image, small_image_size)
        image_list.append(resized_small_image)

    for image in image_list:
        width, height = image.size
        r_total = 0
        g_total = 0
        b_total = 0
        count = 0
        for x in range(0, width):
            for y in range(0, height):
                r, g, b = image.getpixel((x,y))
                r_total += r
                g_total += g
                b_total += b
                count += 1
                average_brightness = int((((r_total + g_total + b_total)/count)/3))
        image_brightness_list.append(average_brightness)
    
    return image_list, image_brightness_list

def get_choices(image_brightness_list: list, large_image_pixels, image_list):
    # TODO: make sure every image is used: get the most similar image if not used, else put a random unused image. if all unused image used up, then put a random image
    choice_list = []
    unique_images = image_list.copy()
    threshold = 40
    for pixel in large_image_pixels:
        possible_matches = []
        for b in image_brightness_list:
            if abs(b-pixel) <= threshold and image_list[image_brightness_list.index(b)] in unique_images:
                possible_matches.append(image_list[image_brightness_list.index(b)])
                
        if len(possible_matches) == 0:
            if len(unique_images) > 0:
                # possible_matches.append(image_list[image_brightness_list.index(random.choice(image_brightness_list))])
                possible_matches.append(random.choice(unique_images))
                print("added random!")
            else:
                possible_matches.append(image_list[image_brightness_list.index(random.choice(image_brightness_list))])

        choice = random.choice(possible_matches)
        choice_list.append(choice)         
        if choice in unique_images:   
            unique_images.remove(choice)

    assert unique_images == []
    return choice_list

def paste(new_image, small_image_size, choice_list):
    w, h = new_image.size
    count = 0
    for x in range(0, w, int(small_image_size)):
        for y in range(0, h, int(small_image_size)):
            new_image.paste(choice_list[count], (x, y, x+int(choice_list[count].size[0]), y+int(choice_list[count].size[1])))
            count += 1

def main():
    args = parse_arguments()
    assert args.final_size % args.small_image_size == 0

    new_image = Image.new('RGBA', (args.final_size, args.final_size))
    large_image = Image.open(args.large_image_path)
    large_image_alpha = Image.open(args.large_image_path)
    large_image_alpha = large_image_alpha.convert('RGBA')
    # scale = int(args.final_size/args.small_image_size)

    print("Resizing large image...")
    # large_image = resize_crop(large_image, scale)
    large_image_alpha = scale_large_image(large_image_alpha, args.final_size, args.small_image_size)
    # large_image_alpha = resize_crop(large_image_alpha, args.final_size)
    # large_image_alpha = large_image_alpha.resize((args.final_size, args.final_size))
    # print((large_image_alpha.size[0], large_image_alpha.size[1]))

    new_image = Image.new('RGBA', (large_image_alpha.size[0], large_image_alpha.size[1]))

    assert new_image.size[0] % args.small_image_size == 0
    assert new_image.size[1] % args.small_image_size == 0
    large_image = large_image.resize((int(new_image.size[0]/args.small_image_size), int(new_image.size[1]/args.small_image_size)))

    print("Getting pixel values from large image...")
    large_image_pixels = get_target_pixels(large_image)
    print("Resizing and gathering pixel data from small images...")
    image_list, image_brightness_list = get_small_averages(args.small_image_folder, args.small_image_size)
    print("Calculating matches for pixels...")
    choice_list = get_choices(image_brightness_list, large_image_pixels, image_list)
    print("pasting images into final image...")
    paste(new_image, args.small_image_size, choice_list)
    final_image = Image.blend(large_image_alpha, new_image, .65)
    print("Finishing!")
    final_image.save(f"{args.final_size}x{args.small_image_size}.png")

if __name__ == '__main__':
    main()