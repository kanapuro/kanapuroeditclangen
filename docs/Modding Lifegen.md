# **Art Additions** {#art-additions}

`This was originally made to be a ClanGen Guide, so this does not have lifegen specific stuff currently. Still a work in progress - sorry for any one who got excited for the stuff I haven't done yet lol`

## **Table of Contents** {#table-of-contents}

***`This guide does not go over high-res or additional sprites`***

`Art Additions`

[`Table of Contents`](#table-of-contents)

[`Lists`](#lists)

[`List`](#list)

[`Preparations`](#preparations)

[`Layout`](#layout)

[`... If the layout file isn't big enough`](#...-if-the-layout-file-isn't-big-enough)

[`What to Download`](#what-to-download)

[`File placement`](#file-placement)

[`List of PNG names (A-Z):`](#list-of-png-names-\(a-z\):)

[`Adding New Pelt Options`](#adding-new-pelt-options)

[`PNG`](#png)

[`Coding`](#coding)

[`Sprites.py`](#sprites.py)

[`Pelts.py`](#pelts.py)

[`Adding New Color Options`](#adding-new-color-options)

[`PNG`](#png-1)

[`Expanding Canvases`](#expanding-canvases)

[`Coding`](#coding-1)

[`Sprites.py`](#sprites.py-1)

[`Pelts.py`](#pelts.py-1)

[`Colour_categories`](#colour_categories)

[`Adding New Eye Colors`](#adding-new-eye-colors)

[`Expanding Canvases`](#expanding-canvases-1)

[`Coding`](#coding-2)

[`Sprites.py`](#sprites.py-2)

[`Pelts.py`](#pelts.py-2)

[`Accessories`](#accessories)

[`: Adding to existing PNG`](#:-adding-to-existing-png)

[`PNG`](#png-2)

[`Coding`](#coding-3)

[`Sprites.py`](#sprites.py-3)

[`medcatherbs_data`](#medcatherbs_data)

[`Pelts.py`](#pelts.py-3)

[`Cats.py & scar_events.py`](#cats.py-&-scar_events.py)

[`acc_display.json`](#acc_display.json)

[`: Adding new PNG`](#:-adding-new-png)

[`PNG`](#png-3)

[`Coding`](#coding-4)

[`Sprites.py`](#sprites.py-4)

[`Pelts.py`](#pelts.py-4)

[`Cats.py & scar_events.py`](#cats.py-&-scar_events.py-1)

[`Utility.py`](#utility.py)

[`acc_display.json`](#acc_display.json-1)

[`Adding to White Patches`](#adding-to-white-patches)

[`PNG`](#png-4)

[`Coding`](#coding-5)

[`Sprites.py`](#sprites.py-5)

[`pelts.py`](#pelts.py-5)

[`Vit and Colorpoints`](#vit-and-colorpoints)

[`Adding to Tortie Pattern`](#adding-to-tortie-pattern)

[`PNG`](#png-5)

[`Coding`](#coding-6)

[`sprites.py`](#sprites.py-6)

[`pelts.py`](#pelts.py-6)

[`Adding to Skins`](#adding-to-skins)

[`Expanding Canvases`](#expanding-canvases-2)

[`Coding`](#coding-7)

[`sprites.py`](#sprites.py-7)

[`pelts.py`](#pelts.py-7)

[`Adding to Scars`](#adding-to-scars)

[`sprites.py`](#sprites.py-8)

[`pelts.py`](#pelts.py-8)

[`Adding to tints`](#adding-to-tints)

[`Adding Symbols`](#adding-symbols)

[`Adding Camps`](#adding-camps)

[`Adding Patrol Art`](#adding-patrol-art)

## **Lists** {#lists}

`You might see a lot of brackets ( [ ] ) in this guide. These are called lists, and are exactly what the name suggests. They allow the coder to store multiple objects in a single variant, primarily for data storing purposes.`

`In clangen, you will see these a lot while coding sprite options. Lists allows clangen to specify what each sprite is named, where they are in the spritesheet, and what categories the sprites are in. Here's an example:`

`accessory_data = [`  
	`["ONE","TWO","THREE"],`  
	`["FOUR","FIVE","SIX"],`  
  `],`

*`It's easier to think of these as boxes`*`. Everyone has seen those plastic dividers you put in your kitchen cabinets, right? Well, this functions the same way.` 

* `"accessory_data" is the cabinet space holding all the objects. [] signifies the whole space.`  
* `The brackets inside "accessory_data" are the dividers. They're placed inside the cabinet ([[]]) and they store their own objects ([["ONE"]]). Think of every row on the spritesheet as a divider`

# **List** {#list}

`List of what to go over: (ALL OF THIS FOR STABLE)`

- [x] ~~`Preparations`~~  
      - [x] ~~`Layout`~~  
      - [x] ~~`What to download`~~  
      - [x] ~~`File placement`~~  
      - [x] ~~`Provide a drive with the boxes layout and lineart. Use the biggest file clangen has - which is white patches`~~  
- [x] ~~`Adding pelt types`~~  
- [x] ~~`adding new color options`~~   
- [x] ~~`Adding new eye colors (for both eyes/eyes2)`~~  
- [x] ~~`Accessories (adding to existing file and adding new png)`~~  
- [x] ~~`Adding to white patches`~~  
- [x] ~~`Adding to tortie markings`~~  
- [ ] `Adding to skins`  
- [ ] `Adding to scars`  
- [ ] `Adding tints (mention new tints would be more involved with the lifegen customizer)`  
- [ ] `Adding symbols.... Ugh`  
- [ ] `Adding a new camp`

# **Preparations** {#preparations}

`Personally, I favor having everything laid out and planned before diving in. It gives me a sense of security and lays out a clear direction to follow. Otherwise, I just feel lost - and you kinda don't want that while modding.`

`If you're not that type of person or you get bored with planning, please refer to the provided drive link! This will have all the PNG files you may need starting out (click the three dots, select details for connected descriptions), but I still recommend at least reading through "layout"!`

## **Layout** {#layout}

`The PNG files have to be in a specific layout. The sprites are coded kinda like layers that are cut out and placed on the cats. If they're not laid out specifically, then you might experience pelts, eyes, etc "flying" off the cats.`

* `If you want to know more about which order the sprites are layered or just how clangen does their sprites, please read clangen's sprite documentation!`

`Each sprite (or pose) is in a 50x50 pixel box. The sprites are 3x7 or 150x350, and there are a total of 21 poses. Each sprite option in the PNG is within the 150x350 barrier - if your art strays out of it, that's when you get stuff appearing in other sprite options. If that makes sense!`

`HOWEVER, there is a great way to avoid this! All it involves is the ~background colors~. Now, you may be wondering what the hell I mean. Check out this drive and click on the checker box png! This png is a "visual guide" of sorts. Example below.`

`![][image1]`  
*`Example of the whitepatches.png with my method`*

`I use this method with practically every PNG within clangen's sprite folder. Personally, I see things better when the background is blue, so that's why mine is that way. The red lines are the "barrier", which show where the box stops and the new one starts.`

`And there you go! You should be safe from stray pixels, flying sprite options, or options intersecting into each other.`

### **... If the layout file isn't big enough** {#...-if-the-layout-file-isn't-big-enough}

`If for some reason the provided file isn't big enough either in height or width, you need to do some math to extend the canvas size. Since each box is a 50 pixel box, the math should be really simple.`

`Here's how I do it with FireAlpaca (shout out to the easiest drawing program I ever used)`

- `Navigate to the top and select "edit"`  
- `Select "canvas size..." (or ctrl + alt + c)`  
- `Specify left if you need extend width, specify top center if you need to extend height`  
- `IF extending width, add 150 x how many new rows you need`  
- `IF extending height, add 350 x how many new rows you need`

`From there, copy the layer with the checker boxes and drag it over to align with the extended space. Merge the checker box layers, then do the same for the lineart layer if applicable.`

## **What to Download** {#what-to-download}

`This kinda depends on what you want to do with the files, but it's generally good to note that installing source gives you access to the script folder. This is where all the backend code is held.`

`Want to add a new option? Want to rename a specific color? Want to add physical characteristics? Source.` 

`Want to just do a retexture mod? Want to do a high-res mod? Want to do a rainbow mod that simply replaces the files that already exist? Application.`

`However, I highly recommend the source download for any type of modding. Yes, it's difficult to install compared to application, but having access to the code is always a win in my books. Of course, though, it's not necessarily needed if you're not adding anything new.`

***`Outside of the clangen version, you also need:`***

1. `A program that offers pixel brushes (or anti-aliasing). It doesn't have to be fancy.`  
2. `Access to the sprite files for ClanGen.`   
   * `If you're a phone user, you can install all the files individually via Github (view the file you want to download, select the three dots at the top, and select download)`  
3. `A lot of time and patience depending the complexity of your mod`

`Optional, but I provide a drive linking to png files that generally make it easier to add or edit sprites! Please look at "layout" for more information.`

## **File placement** {#file-placement}

`If you've never looked in the sprite folder before, you might get a bit overwhelmed. That's okay! I'll list what's in the folder here and group them by function/section.`

### **List of PNG names (A-Z):** {#list-of-png-names-(a-z):}

- `Remember that ClanGen developers are a mixed bag of regions and languages, so make sure you're naming your files exactly to the original! Just because one section of the game has american spelling, doesn't mean all of them will`

**`Pelts`**`: (14)`

`agouticolours`  
`bengalcolours`  
`classiccolours`  
`mackerelcolours`  
`marbledcolours`  
`maskedcolours`  
`rosettecolours`  
`singlecolours`  
`singlestripecolours`  
`smokecolours`  
`sokokecolours`  
`speckledcolours`  
`tabbycolours`  
`tickedcolours`

**`Linearts`**`: (6)`

`aprilfoolslineart`  
`aprilfoolslineartdead`  
`aprilfoolslineartdf`  
`lineart`  
`lineartdead`  
`lineartdf`

**`Accessories`**`: (6)`

`bellcollars`  
`bowcollars`  
`collars`  
`medcatherbs`  
`nyloncollars`  
`wild`

**`Fading`**`: (3)`

`fadedarkforest`  
`fademask`  
`fadestarclan`

**`Light and Shadows`**`: (2)`

`lightingnew`  
`shadersnewwhite`

**`MISC`**`: (9)`

`error_placeholder`  
`eyes`  
`eyes2`  
`missingscars`  
`scars`  
`skin`  
`symbols`  
`tortiepatchesmasks`  
`whitepatches`

**`Faded Folder`**`:`  
*`The Faded folder contains the fading sprites you usually see when a cat is completely faded. These are individual pngs of a single pose for each age group depicting either SC or DF`*

`faded_adol`  
`faded_adol_df`  
`faded_adult`  
`faded_adult_df`  
`faded_kitten`  
`faded_kitten_df`  
`faded_newborn`  
`faded_newborn_df`  
`faded_senior`  
`faded_senior_df`

**`Dicts Folder`**`:`  
*`Where the tints are held! These are not actual pngs - rather JSONs that hold code specifying the tint colors and which pelt color gets them naturally`*

`tint.json`  
`white_patches_tint.json`

**`Paralyzed Folder`**`:`

***`NOTE`**`: This Folder does not actually have a function anymore, but I believe the ClanGen developers keep it in the sprites folder to credit the original artist`*

# **Adding New Pelt Options** {#adding-new-pelt-options}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`So you want to add a new pelt option! A brief rundown: Pelt options are pelt patterns such as singlecolour, singlestripe, bengal, ect. They come in an assortment of different colors and typically range in complexity!`

**`In this section, I'm going to use "spotscolours" as an example!`**

## **PNG** {#png}

`First, you'll need to actually draw your new pelt option. Refer to layout if you haven't already!`

`For uniformity, name your png like "[peltname]colours".` 

`Now, the order of the color options within the file does matter! They're categorized separately in the code, so putting them in the png out of order will simply incorrectly label your colors. Below is the order of colors - each [] is a row in the png:`

        color\_categories \= \[  
            \["WHITE", "PALEGREY", "SILVER", "GREY", "DARKGREY", "GHOST", "BLACK"\],  
            \["CREAM", "PALEGINGER", "GOLDEN", "GINGER", "DARKGINGER", "SIENNA"\],  
            \["LIGHTBROWN", "LILAC", "BROWN", "GOLDEN-BROWN", "DARKBROWN", "CHOCOLATE"\],  
        \]  
*`Found on line 370 in sprites.py`*

`Now before you go ham, I recommend using a method called "masking". This method involves making a separate layer for each detail section of the pelt. This makes it so much easier to create color options for pelts, as all you need to do is duplicate the folder, drag and align the new folder to the next option, and recolor each new layer.`

`Here's a finicky example of a potential mask for spotscolour:`

`![][image2]`  
*`Obviously color in the lines lol`*

`Every color you see here is its own layer within a single folder. I usually call these "templates". I personally like to go light to dark so I understand my process while creating the mask, and this gives you the opportunity to plan out how you want your pelt(s) to look, so to speak.`

`You might not see the vision because of my eye bleeding art skills but I promise masking the pelts like this will help so much in the long run, especially if you decide you want to add more colors later.`

**`Make sure to delete the lineart and background layer when you're done!`** `Otherwise it might look a little strange in game. Just a tad.`

## **Coding** {#coding}

`Once the PNG is created and you're happy with how it looks, you're going to plop it directly into the sprites folder. Make sure to write the name of the PNG somewhere as you're going to need it later while coding it in.`

### **Sprites.py** {#sprites.py}

`{scripts > cat folder}`

`First file we're going to edit is sprites.py. This can be found within the path: scripts > cats > sprites.py. Scroll down to about like 150.`

`The first thing you have to do when adding a new png into the game is to make sure the game knows it's there. We do that by editing "for x in []"`

        for x in \[  
            "lineart",  
            "lineartdf",  
            "lineartdead",  
            "eyes",  
            "eyes2",  
            "skin",  
            "scars",  
            "missingscars",  
            "medcatherbs",  
            "wild",  
            "collars",  
            "bellcollars",  
            "bowcollars",  
            "nyloncollars",  
            "singlecolours",  
            "speckledcolours",  
            "tabbycolours",  
            "bengalcolours",  
            "marbledcolours",  
            "rosettecolours",  
            "smokecolours",  
            "tickedcolours",  
            "mackerelcolours",  
            "classiccolours",  
            "sokokecolours",  
            "agouticolours",  
            "singlestripecolours",  
            "maskedcolours",  
            "shadersnewwhite",  
            "lightingnew",  
            "whitepatches",  
            "tortiepatchesmasks",  
            "fademask",  
            "fadestarclan",  
            "fadedarkforest",  
            "symbols",  
		"spotscolours",  
        \]:

`The highlighted part at the bottom is the png I want to add to the list. Do not add .png to the end! Just the name. Make sure it's surrounded by quotes and have an ending comma - "spotscolours",`

`From there, scroll through the file until you see color_types at around line 376. We're also going to add the new png to this list, like below.`

color\_types \= \[  
            "singlecolours",  
            "tabbycolours",  
            "marbledcolours",  
            "rosettecolours",  
            "smokecolours",  
            "tickedcolours",  
            "speckledcolours",  
            "bengalcolours",  
            "mackerelcolours",  
            "classiccolours",  
            "sokokecolours",  
            "agouticolours",  
            "singlestripecolours",  
            "maskedcolours",  
		"spotscolours",  
       \]

`All this does is essentially lets the game know that the png you added is a pelt option.`

`Save, and we're done with this file!`

`Very easy, right?`

### **Pelts.py** {#pelts.py}

`{scripts > cat folder}`

`Okay now navigate to the pelts.py, which is in the same place as your sprites.py. You don't need to scroll here, as you're met with sprite_names straight away.`

`What sprite_names essentially does is gives your pelt option a name! If I were to add spotscolours, I'd probably give them the name spots. Like below:`

    sprites\_names \= {  
        "SingleColour": 'single',  
        'TwoColour': 'single',  
        'Tabby': 'tabby',  
        'Marbled': 'marbled',  
        'Rosette': 'rosette',  
        'Smoke': 'smoke',  
        'Ticked': 'ticked',  
        'Speckled': 'speckled',  
        'Bengal': 'bengal',  
        'Mackerel': 'mackerel',  
        'Classic': 'classic',  
        'Sokoke': 'sokoke',  
        'Agouti': 'agouti',  
        'Singlestripe': 'singlestripe',  
        'Masked': 'masked',  
	  'Spots': 'spots',  
        'Tortie': None,  
        'Calico': None,  
    }

`You might be wondering - what's the point of putting this twice? Great question! It's to separate the difference between what is a pelt name and what can be a pelt base. As you can see, tortie and calico are pelt names but they can't exactly be a base (like you can't make a calico cat double calico).`

`Make sure to capitalize the left but don't capitalize the right! 'Spots': 'spots',`

`Scroll down until about line 54 where you see tortiebases = []. We're simply going to add the name of the pelt, like we did above`

    tortiebases \= \['single', 'tabby', 'bengal', 'marbled', 'ticked', 'smoke', 'rosette', 'speckled', 'mackerel',  
                   'classic', 'sokoke', 'agouti', 'singlestripe', 'masked', 'spots'\]

`Don't put a comma after your added pelt!`

`Scroll until about line 102. This is where we're going to specify the categories of pelts. There's five options: tabbies, spotted, plain, exotic, and torties. In my example, I'm putting my pelt into spotted but add yours to wherever fits the most.`

    tabbies \= \["Tabby", "Ticked", "Mackerel", "Classic", "Sokoke", "Agouti"\]  
    spotted \= \["Speckled", "Rosette", "Spots"\]  
    plain \= \["SingleColour", "TwoColour", "Smoke", "Singlestripe"\]  
    exotic \= \["Bengal", "Marbled", "Masked"\]  
    torties \= \["Tortie", "Calico"\]  
    pelt\_categories \= \[tabbies, spotted, plain, exotic, torties\]  
*`Make sure it's capitalized here!`*

`Scroll until around line 990. This is the description of the pelt used in the alliances. You can be as detailed as you want, but make sure c_n is somewhere in the text. c_n is referring to color_name!`

        pattern\_des \= {  
            "Tabby": "c\_n tabby",  
            "Speckled": "speckled c\_n",  
            "Bengal": "unusually dappled c\_n",  
            "Marbled": "c\_n tabby",  
            "Ticked": "c\_n ticked",  
            "Smoke": "c\_n smoke",  
            "Mackerel": "c\_n tabby",  
            "Classic": "c\_n tabby",  
            "Agouti": "c\_n tabby",  
            "Singlestripe": "dorsal-striped c\_n",  
            "Rosette": "unusually spotted c\_n",  
            "Sokoke": "c\_n tabby",  
            "Masked": "masked c\_n tabby",  
		 "Spots": "spotted c\_n"  
        }

`If you want to be true to how the pelts are described, make sure to only use at most two descriptive terms.`

`I honestly wasn't too sure about the rest of the description code, so I'm not going to cover that since it's not going to break your game if you don't edit it.`

# **Adding New Color Options** {#adding-new-color-options}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`Adding a new color option involves editing all the existing pelt pngs in your sprites folder, plus any additional pelt options you've added if applicable, since colors are categorized in the code separately from the PNGs.`

* `If you're unsure which files are pelt pngs, please refer to "file placement"`

`I recommend duplicating the pelt pngs, adding them to a separate folder, and renaming them to be "bengal modified" or similar just to distinguish them from the original files. Later you can rename them and replace the original with your own.`

## **PNG** {#png-1}

`Now, obviously it can be kinda hard to follow the original pelts if there isn't an exact mask available. Some pngs have the mask for all sprites within the file, while others do not. You can choose to use the provided markings or make your own!`

* `If you have access to the discord server, please look in #sprites pins for pattern templates made by doe6143`

`I recommend just drawing over the markings on the pelt in a bright, clearly distinguishable color (like hot pink, red, etc), then recoloring them to your heart's desire.`  
`![][image3]`  
*`Example of this method while fixing sprites`*

**`NOTE`**`: For uniformity, most of the pelt options are just markings placed upon the singlecolor pelt option.` 

`If you want to be true to how it's originally done, start with singlecolor then slowly move to the more detailed pelts like bengal, using the singlecolor from before as the base underneath.`

**`NOTE`**`: Newborns are slightly different from the other sprites! This is because naturally irl, cats don't usually pop out as what they'll look like as an adult.` 

* *`Obviously as a mod creator you don't have to follow this detail.`*

**`Make sure to delete the lineart and background layer when you're done!`** `Otherwise it might look a little strange in game. Just a tad.`

### **Expanding Canvases** {#expanding-canvases}

`If you're adding multiple different colors at once, then you will need to expand the canvas size to do what you want. Here's how I do it with FireAlpaca:`

- `Navigate to the top and select "edit"`  
- `Select "canvas size..." (or ctrl + alt + c)`  
- `Specify top center since we're extending height`  
- `Add 350 x how many new rows you need`  
  * `If you're planning to add 7-14 new colors, then it'll be 350 x 2, for example`

`If your program doesn't work the way mine does, please consider searching up "how to expand canvas side in [art program]" in your browser`

## **Coding** {#coding-1}

`Once your colors are done for every pelt file and you're happy with how they look, replace the files in the sprites folder with your modified one. Or just save if you're editing the files directly.`

`From here, name your colors. Write down the order in which the colors are placed within the pngs. For this section, I am going to use "fawn" and "rusty" as examples.`

### **Sprites.py** {#sprites.py-1}

`First, we'll be navigating to sprites.py. This file is in your scripts > cats . We'll only need to do one thing here.`

`Scroll down until line 369, color_catagories. You're going to see a list of colors. Each bracket [] symbolizes one row.`

        color\_categories \= \[  
            \["WHITE", "PALEGREY", "SILVER", "GREY", "DARKGREY", "GHOST", "BLACK"\],  
            \["CREAM", "PALEGINGER", "GOLDEN", "GINGER", "DARKGINGER", "SIENNA"\],  
            \["LIGHTBROWN", "LILAC", "BROWN", "GOLDEN-BROWN", "DARKBROWN", "CHOCOLATE"\],  
		 \["FAWN", "RUSTY"\],  
        \]  
*`Make sure the names are UPPERCASE`*

**`Always, always follow what you added to the png.`** `If you have fawn and rusty, but rusty is underneath fawn on the png instead of next to it, then you have to add rusty to a new row rather than putting them in the same bracket.`

### **Pelts.py** {#pelts.py-1}

`Now, navigate it to pelts.py which is in the same area as sprites.py.` 

`Scroll until line 30, pelt_colours. You will see three sections here: pelt_colours, pelt_c_no_white, pelt_c_no_bw.`

* **`Pelt_colours`** `lists all the colors that can be generated`  
* **`Pelt_c_no_white`** `lists all the colors that are NOT white, aka WHITE`  
* **`Pelt_c_no_bw`** `lists all the colors that are NOT black, aka GHOST and BLACK`

    pelt\_colours \= \[  
        'WHITE', 'PALEGREY', 'SILVER', 'GREY', 'DARKGREY', 'GHOST', 'BLACK', 'CREAM', 'PALEGINGER',  
        'GOLDEN', 'GINGER', 'DARKGINGER', 'SIENNA', 'LIGHTBROWN', 'LILAC', 'BROWN', 'GOLDEN-BROWN', 'DARKBROWN',  
        'CHOCOLATE', 'FAWN', 'RUSTY'  
    \]  
    pelt\_c\_no\_white \= \[  
        'PALEGREY', 'SILVER', 'GREY', 'DARKGREY', 'GHOST', 'BLACK', 'CREAM', 'PALEGINGER',  
        'GOLDEN', 'GINGER', 'DARKGINGER', 'SIENNA', 'LIGHTBROWN', 'LILAC', 'BROWN', 'GOLDEN-BROWN', 'DARKBROWN',  
        'CHOCOLATE', 'FAWN', 'RUSTY'  
    \]  
    pelt\_c\_no\_bw \= \[  
        'PALEGREY', 'SILVER', 'GREY', 'DARKGREY', 'CREAM', 'PALEGINGER',  
        'GOLDEN', 'GINGER', 'DARKGINGER', 'SIENNA', 'LIGHTBROWN', 'LILAC', 'BROWN', 'GOLDEN-BROWN', 'DARKBROWN',  
        'CHOCOLATE', 'FAWN', 'RUSTY'  
    \]  
*`Note: The indents don't matter. They're for readability purposes`*

`My examples, fawn and rusty do not need anything fancy. However, if you're adding colors that are practically white or black, keep in mind that clangen filters those.`

`Alright, now we're going to scroll until line 110 - sprite_colors. It's basically the same deal as above, but now we're going to add our colors by category`

    single\_colours \= \[  
        'WHITE', 'PALEGREY', 'SILVER', 'GREY', 'DARKGREY', 'GHOST', 'BLACK', 'CREAM', 'PALEGINGER',  
        'GOLDEN', 'GINGER', 'DARKGINGER', 'SIENNA', 'LIGHTBROWN', 'LILAC', 'BROWN', 'GOLDEN-BROWN', 'DARKBROWN',  
        'CHOCOLATE', 'FAWN', 'RUSTY'  
    \]  
    ginger\_colours \= \['CREAM', 'PALEGINGER', 'GOLDEN', 'GINGER', 'DARKGINGER', 'SIENNA', 'RUSTY'\]  
    black\_colours \= \['GREY', 'DARKGREY', 'GHOST', 'BLACK'\]  
    white\_colours \= \['WHITE', 'PALEGREY', 'SILVER'\]  
    brown\_colours \= \['LIGHTBROWN', 'LILAC', 'BROWN', 'GOLDEN-BROWN', 'DARKBROWN', 'CHOCOLATE', 'FAWN'\]  
    colour\_categories \= \[ginger\_colours, black\_colours, white\_colours, brown\_colours\]

`And there you go! Save the file and test it out.`

#### **Colour\_categories** {#colour_categories}

`If you decide you want to add a new category for colors, then follow this!`

`Okay, so! Let me first explain what the categories do. It's a way to add weight (or give a chance) to each color group via inheritance (genetics). This makes sure the generation of colors match the clans population.`

`This could be useful if you want to add "special" colors that only generate once in a blue moon, or if you want to add colorful pelts (like green, purple, etc) but don't want them to overtake the clan.`

`First - name your category. As an example, I'm going to use "colourful_colours" for the duration of this section.`

`Navigate to line 110 (#SPRITE NAMES) within your pelts.py. We're going to add the category here.`

    single\_colours \= \[  
        'WHITE', 'PALEGREY', 'SILVER', 'GREY', 'DARKGREY', 'GHOST', 'BLACK', 'CREAM', 'PALEGINGER',  
        'GOLDEN', 'GINGER', 'DARKGINGER', 'SIENNA', 'LIGHTBROWN', 'LILAC', 'BROWN', 'GOLDEN-BROWN', 'DARKBROWN',  
        'CHOCOLATE', 'GREEN', 'RED', 'RAINBOW'  
    \]  
    ginger\_colours \= \['CREAM', 'PALEGINGER', 'GOLDEN', 'GINGER', 'DARKGINGER', 'SIENNA'\]  
    black\_colours \= \['GREY', 'DARKGREY', 'GHOST', 'BLACK'\]  
    white\_colours \= \['WHITE', 'PALEGREY', 'SILVER'\]  
    brown\_colours \= \['LIGHTBROWN', 'LILAC', 'BROWN', 'GOLDEN-BROWN', 'DARKBROWN', 'CHOCOLATE'\]  
    colourful\_colours \= \['GREEN', 'RED', 'RAINBOW'\]  
    colour\_categories \= \[ginger\_colours, black\_colours, white\_colours, brown\_colours, colourful\_colours\]

`Next, scroll til line 470 - #weights for each colour group`

`If you're confused - this code indicates which color can be inherited by a parent.` 

`So using ginger_colours as an example, ginger-colored cats have the highest chance (40) to have gingered kittens and a slight chance (10) to have brown kittens. Black and white are not possible for ginger cats to have, unless parent 2 is a black/white cat.`

            if p\_ in Pelt.ginger\_colours:  
                add\_weight \= (40, 0, 0, 10)

`Add_weight goes in the order of : (ginger_colours, black_colours, white_colours, brown_colours)`

`With our example addition, colourful_colours, there will have to be a fifth section to the weights. We'll do that like this:`

* *`With every additional category, you will need to add a new section (,0) to the weights and a new elif p_ in section to the file`*

        \# Weights for each colour group. It goes: (ginger\_colours, black\_colours, white\_colours, brown\_colours, colourful\_colours)  
        weights \= \[0, 0, 0, 0, 0\]  
        for p\_ in par\_peltcolours:  
            if p\_ in Pelt.ginger\_colours:  
                add\_weight \= (40, 0, 0, 10, 0)  
            elif p\_ in Pelt.black\_colours:  
                add\_weight \= (0, 40, 2, 5, 0)  
            elif p\_ in Pelt.white\_colours:  
                add\_weight \= (0, 5, 40, 0, 0)  
            elif p\_ in Pelt.brown\_colours:  
                add\_weight \= (10, 5, 0, 35, 0)  
            elif p\_ in Pelt.colourful\_colours:  
                add\_weight \= (20, 20, 0, 20, 40\)  
            elif p\_ is None:  
                add\_weight \= (40, 40, 40, 40, 40)  
            else:  
                add\_weight \= (0, 0, 0, 0, 0)

            for x in range(0, len(weights)):  
                weights\[x\] \+= add\_weight\[x\]

            \# A quick check to make sure all the weights aren't 0  
            if all(\[x \== 0 for x in weights\]):  
                weights \= \[1, 1, 1, 1, 1\]

*`All the highlighted blue is what I added to the file!`*

`This should be all you need to do, unless you want to get fancy with alliance descriptions. I will not go over that right now, cause I simply just don't understand it lol - and it shouldn't break your game if you don't edit it.`

`However, if you want to look at it, mass search one of the categories in the file (like white_colours) and it should take you to the code.`

# **Adding New Eye Colors** {#adding-new-eye-colors}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`Eye colors are very simple - it's just 10 pixels max for each sprite. However, for eye colors you have to edit two files - eyes and eyes2. Eyes2 is the heterochromia file.`

`I recommend doing the eyes.png first, copy your additions to eyes2 and delete the left eye of each sprite.`

`Because of the simplicity of the file, I don't think I need to explain how to create eyes. Please check out "layout" for the png files I recommend using while making new options!`

### **Expanding Canvases** {#expanding-canvases-1}

`If you're adding multiple different colors at once, then you will need to expand the canvas size to do what you want. Here's how I do it with FireAlpaca:`

- `Navigate to the top and select "edit"`  
- `Select "canvas size..." (or ctrl + alt + c)`  
- `Specify top center since we're extending height`  
- `Add 350 x how many new rows you need`  
  * `If you're planning to add 7-14 new colors, then it'll be 350 x 2, for example`

`If your program doesn't work the way mine does, please consider searching up "how to expand canvas side in [art program]" in your browser`

## **Coding** {#coding-2}

`Once your eye colors are done and you're happy with how they look, replace the files in the sprites folder with your modified one. Or just save if you're editing the files directly.`

**`Make sure to delete the lineart and background layer when you're done!`** `Otherwise it might look a little strange in game. Just a tad.`

### **Sprites.py** {#sprites.py-2}

`{scripts > cats} Scroll until line 183 - eye_colours`

`Here, we're going to add the eye colors you added to the png. I'll be using ORANGE as an example.`

`If it's in row two:`  
        eye\_colors \= \[  
            \[  
                "YELLOW",  
                "AMBER",  
                "HAZEL",  
                "PALEGREEN",  
                "GREEN",  
                "BLUE",  
                "DARKBLUE",  
                "GREY",  
                "CYAN",  
                "EMERALD",  
                "HEATHERBLUE",  
                "SUNLITICE",  
            \],  
            \[  
                "COPPER",  
                "SAGE",  
                "COBALT",  
                "PALEBLUE",  
                "BRONZE",  
                "SILVER",  
                "PALEYELLOW",  
                "GOLD",  
                "GREENYELLOW",  
		    "ORANGE",  
            \],  
        \]

`If it's in a new row:`  
        eye\_colors \= \[  
            \[  
                "YELLOW",  
                "AMBER",  
                "HAZEL",  
                "PALEGREEN",  
                "GREEN",  
                "BLUE",  
                "DARKBLUE",  
                "GREY",  
                "CYAN",  
                "EMERALD",  
                "HEATHERBLUE",  
                "SUNLITICE",  
            \],  
            \[  
                "COPPER",  
                "SAGE",  
                "COBALT",  
                "PALEBLUE",  
                "BRONZE",  
                "SILVER",  
                "PALEYELLOW",  
                "GOLD",  
                "GREENYELLOW",  
            \],  
		\[  
		    "ORANGE",  
		\],  
        \]

**`Always, always follow what you added to the png.`** `It is very case sensitive!!`

### **Pelts.py** {#pelts.py-2}

`{scripts > cats} Scroll to line 58 - eye_colours`

`We'll now be adding the eye color option to the pool, plus what color category it would fit into.`

    eye\_colours \= \['YELLOW', 'AMBER', 'HAZEL', 'PALEGREEN', 'GREEN', 'BLUE', 'DARKBLUE', 'GREY', 'CYAN', 'EMERALD','PALEBLUE',  
                   'PALEYELLOW', 'GOLD', 'HEATHERBLUE', 'COPPER', 'SAGE', 'COBALT', 'SUNLITICE', 'GREENYELLOW','BRONZE', 'SILVER', 'ORANGE'\]  
    yellow\_eyes \= \['YELLOW', 'AMBER', 'PALEYELLOW', 'GOLD', 'COPPER', 'GREENYELLOW', 'BRONZE', 'SILVER', 'ORANGE'\]  
    blue\_eyes \= \['BLUE', 'DARKBLUE', 'CYAN', 'PALEBLUE', 'HEATHERBLUE', 'COBALT', 'SUNLITICE', 'GREY'\]  
    green\_eyes \= \['PALEGREEN', 'GREEN', 'EMERALD', 'SAGE', 'HAZEL'\]  
*`The indentation does not matter - it is for readability`*

`Scroll to line 121 - eye_sprites`

    eye\_sprites \= \[  
        'YELLOW', 'AMBER', 'HAZEL', 'PALEGREEN', 'GREEN', 'BLUE', 'DARKBLUE', 'BLUEYELLOW', 'BLUEGREEN',  
        'GREY', 'CYAN', 'EMERALD', 'PALEBLUE', 'PALEYELLOW', 'GOLD', 'HEATHERBLUE', 'COPPER', 'SAGE', 'COBALT',  
        'SUNLITICE', 'GREENYELLOW', 'BRONZE', 'SILVER', 'ORANGE'  
    \]

`Anddd you're done!`

# **Accessories** {#accessories}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`Accessories are items the cats wear in game. Currently in stable, they can only wear one accessory at a time. This is changed in development`

**`NOTE`**`: Accessories cannot share names in the code. They can share display names, but you cannot have two "DAISY" accessories. This can be easily fixed by adding a number (DAISY2) or giving it a descriptive name (DAISYCLUSTER)`

## **: Adding to existing PNG** {#:-adding-to-existing-png}

### **PNG** {#png-2}

`This is the same process as adding a new color for pelts - all you need to do is simply add your additions to the existing PNG (in this example I'll be using medcatherbs) by using the layout png guides I provide in "layout".`

* **`NOTE`**`: Make sure when you're done, you're deleting the background checker box pattern and lineart layer. Otherwise your sprites will look a little weird. Just a tad.`

`![][image4]`  
*`Example adding an unfinished accessory, "arrowhead", to medcatherbs`*

**`NOTE`**`: If you'd like to do it the same way ClanGen does, be aware that there are a few ground rules they follow.` 

- `Accessories must cover less than 1/3rd of a cat`  
- `The accessory must have a lineart. Inside the sprite is a darker color than the accessory (if it's a daisy, the lineart is a dark grey), while if it's outside the sprite, the lineart is black`

`![][image5]`

- `ClanGen uses shadow to dictate depth. If it's behind the cat, make it darker`   
- `Be mindful of lost limb scars. Only no/half tail has code for certain accessories`

### **Coding** {#coding-3}

`Okay, once you're happy with your accessories, you can now save the file (if`   
`you're editing the png directly) or replace the png (if you duplicated the png to make edits).`

`In this section, I'm going to use the png "medcatherbs" and the accessory "ARROWHEAD" as examples.`

#### **Sprites.py** {#sprites.py-3}

`{scripts > cat folder}`

`Since we're adding to an existing file, we don't need to do anything fancy. We're just going to add our accessories to the PNGs code.`

`Search the file for the name of the png you edited. For me, it's going to be "medcatherbs". The first thing I'm going to edit is "medcatherbs_data". All you're going to do is add your accessory(ies) to the data, like below.`

`If you placed it beside an accessory:`

        medcatherbs\_data \= \[  
            \[  
                "MAPLE LEAF",  
                "HOLLY",  
                "BLUE BERRIES",  
                "FORGET ME NOTS",  
                "RYE STALK",  
                "CATTAIL",  
                "POPPY",  
                "ORANGE POPPY",  
                "CYAN POPPY",  
                "WHITE POPPY",  
                "PINK POPPY",  
            \],  
            \[  
                "BLUEBELLS",  
                "LILY OF THE VALLEY",  
                "SNAPDRAGON",  
                "HERBS",  
                "PETALS",  
                "NETTLE",  
                "HEATHER",  
                "GORSE",  
                "JUNIPER",  
                "RASPBERRY",  
                "LAVENDER",  
            \],  
            \[  
                "OAK LEAVES",  
                "CATMINT",  
                "MAPLE SEED",  
                "LAUREL",  
                "BULB WHITE",  
                "BULB YELLOW",  
                "BULB ORANGE",  
                "BULB PINK",  
                "BULB BLUE",  
                "CLOVER",  
                "DAISY",  
		     "ARROWHEAD",  
            \],  
        \]  
*`Don't actually do this for medcatherb, follow the medcatherb_data section below`*

`If you placed your accessory(ies) on a separate row:`

        medcatherbs\_data \= \[  
            \[  
                "MAPLE LEAF",  
                "HOLLY",  
                "BLUE BERRIES",  
                "FORGET ME NOTS",  
                "RYE STALK",  
                "CATTAIL",  
                "POPPY",  
                "ORANGE POPPY",  
                "CYAN POPPY",  
                "WHITE POPPY",  
                "PINK POPPY",  
            \],  
            \[  
                "BLUEBELLS",  
                "LILY OF THE VALLEY",  
                "SNAPDRAGON",  
                "HERBS",  
                "PETALS",  
                "NETTLE",  
                "HEATHER",  
                "GORSE",  
                "JUNIPER",  
                "RASPBERRY",  
                "LAVENDER",  
            \],  
            \[  
                "OAK LEAVES",  
                "CATMINT",  
                "MAPLE SEED",  
                "LAUREL",  
                "BULB WHITE",  
                "BULB YELLOW",  
                "BULB ORANGE",  
                "BULB PINK",  
                "BULB BLUE",  
                "CLOVER",  
                "DAISY",  
            \],  
		\[  
		     "ARROWHEAD",  
		\],  
        \]  
*`Follow the medcatherb_data section below if you're editing this in particular`*

***`Always follow what you did to the PNG`***`! Make sure your accessory names are in order corresponding to what you added to the PNG, plus make sure you're being mindful about their placement.`

**`Accessory names should always be UPPERCASE`**

##### `medcatherbs_data` {#medcatherbs_data}

`Obviously this file is kinda complicated because it's separated into two different datas - medcatherbs_data and dryherbs_data. If you want to add your accessories to medcatherbs_data but it's behind the four accessories at the bottom of the file (aka dry herbs), then you'll need to reposition the accessories.` 

* **`NOTE`**`: If you intend to just keep the accessories with dry herbs, edit dryherbs_data instead`

`You can do this by adding a new row to the file and dragging dry herbs to the new row, then placing your additional accessories where the dry herbs originally were. This allows you to simply add your accessories to medcatherbs_data without mucking anything up`

* **`NOTE`**`: Make sure when doing this, you change the enumerate(dryherbs_data) (col, 3) to be (col, 4)`

#### **Pelts.py** {#pelts.py-3}

`{scripts > cat folder}`

`Scroll through the file until you're at line 80, plant_accessories. This is where you categorize the accessories you added. Because I'm adding a tail accessory, I'll be placing mine in two different areas`

    plant\_accessories \= \["MAPLE LEAF", "HOLLY", "BLUE BERRIES", "FORGET ME NOTS", "RYE STALK", "CATTAIL", "POPPY", "ORANGE POPPY", "CYAN POPPY", "WHITE POPPY", "PINK POPPY",  
                        "BLUEBELLS", "LILY OF THE VALLEY", "SNAPDRAGON", "HERBS", "PETALS", "NETTLE", "HEATHER", "GORSE", "JUNIPER", "RASPBERRY", "LAVENDER",  
                        "OAK LEAVES", "CATMINT", "MAPLE SEED", "LAUREL", "BULB WHITE", "BULB YELLOW", "BULB ORANGE", "BULB PINK", "BULB BLUE", "CLOVER", "DAISY",  
                        "CLOVER", "DAISY", "LILY OF THE VALLEY", "HEATHER", "SNAPDRAGON", "GORSE", "BULB WHITE", "BULB YELLOW",  
                        "DRY HERBS", "DRY CATMINT", "DRY NETTLES", "DRY LAURELS", "ARROWHEAD"  
                        \]  
*`Indentation does not matter - it's for readability`*

`Only add your accessory here if the accessory is on the tail. This is important for later`

    tail\_accessories \= \["RED FEATHERS", "BLUE FEATHERS", "JAY FEATHERS", "GULL FEATHERS", "SPARROW FEATHERS", "CLOVER", "DAISY", "ARROWHEAD"\]

#### **Cats.py & scar\_events.py** {#cats.py-&-scar_events.py}

***`IF your accessory is a tail accessory`***`, follow these steps.`

`Navigate to cats.py (scripts folder > cats folder), scroll until line 2043, # remove accessories if need be`

`Here is the code that makes tail accessories invisible if a cat has a tail limb scar, such as no tail and half tail.`

        \# remove accessories if need be  
        if "NOTAIL" in self.pelt.scars and self.pelt.accessory in \[  
            "RED FEATHERS",  
            "BLUE FEATHERS",  
            "JAY FEATHERS",  
            "GULL FEATHERS",  
            "SPARROW FEATHERS",  
            "CLOVER",  
            "DAISY",  
		"ARROWHEAD",  
        \]:  
            self.pelt.accessory \= None  
        if "HALFTAIL" in self.pelt.scars and self.pelt.accessory in \[  
            "RED FEATHERS",  
            "BLUE FEATHERS",  
            "JAY FEATHERS",  
            "GULL FEATHERS",  
            "SPARROW FEATHERS",  
            "CLOVER",  
            "DAISY",  
		"ARROWHEAD",  
        \]:

`You want to do this, otherwise your tail accessory will be flying off kitties with no tails.`

`Theoretically if you want to, you can also add code for other no limb scars, like NOPAW, if your accessory relies on the area the no limb scar removes.`

`You'll also have to edit scar_events.py (scripts > events_module > scar_events) if you want to make sure tail accessories can't be generated for no tail kitties either.`

`Scroll until about line 153, if specialty in ["NOTAIL", "HALFTAIL"]. Add your tail accessories here.`

            specialty \= random.choice(scar\_pool)  
            if specialty in \["NOTAIL", "HALFTAIL"\]:  
                if cat.pelt.accessory in \["RED FEATHERS", "BLUE FEATHERS", "JAY FEATHERS", "GULL FEATHERS", "SPARROW FEATHERS", "CLOVER", "DAISY", "ARROWHEAD"\]:  
                    cat.pelt.accessory \= None

#### **acc\_display.json** {#acc_display.json}

`(resources > dicts > acc_display.json)`

`This file holds all the text you see when the accessory is mentioned in an event or shown on a cat's profile.` 

`Scroll all the way down to the end of the file, and duplicate the code of the last text code. The "id" ("ARROWHEAD") should be exact to how the accessory is written in the .py files.`

 `"INFO": [`  
    `"default should be what you'd like to display on the cat profile",`  
    `"plural and singular will be used on events"`  
  `],`

  },  
  "INDIGONYLON": {  
    "default": "indigo nylon collar",  
    "plural": "indigo nylon collars",  
    "singular": "indigo nylon collar"  
  },  
  "ARROWHEAD": {  
    "default": "arrowhead",  
    "plural": "arrowheads",  
    "singular": "arrowhead"  
  }  
}

`Then boom, you're done! Run the game to make sure everything is working smoothly.`

## **: Adding new PNG** {#:-adding-new-png}

### **PNG** {#png-3}

`Very, very simple. You'll just add your accessory(ies) to a new png and add it to the sprites folder. Write down the name of the png and the order of the accessories in the png somewhere for future reference.`

### **Coding** {#coding-4}

`Once the png is present in the sprites folder and you have everything written`   
`down (name of png, name of accessories in order and row), then we'll head to coding!`

`For this section, I am going to use the file name "toxicplants" and the accessories in this order: (row one) "ARROWHEAD", "YUCCA" (row two) "LILIES", "STOCK"`

#### **Sprites.py** {#sprites.py-4}

`First file we're going to edit is sprites.py. This can be found within the path: scripts > cats > sprites.py. Scroll down to about like 150.`

`The first thing you have to do when adding a new png into the game is to make sure the game knows it's there. We do that by editing "for x in []"`

        for x in \[  
            "lineart",  
            "lineartdf",  
            "lineartdead",  
            "eyes",  
            "eyes2",  
            "skin",  
            "scars",  
            "missingscars",  
            "medcatherbs",  
            "wild",  
            "collars",  
            "bellcollars",  
            "bowcollars",  
            "nyloncollars",  
            "singlecolours",  
            "speckledcolours",  
            "tabbycolours",  
            "bengalcolours",  
            "marbledcolours",  
            "rosettecolours",  
            "smokecolours",  
            "tickedcolours",  
            "mackerelcolours",  
            "classiccolours",  
            "sokokecolours",  
            "agouticolours",  
            "singlestripecolours",  
            "maskedcolours",  
            "shadersnewwhite",  
            "lightingnew",  
            "whitepatches",  
            "tortiepatchesmasks",  
            "fademask",  
            "fadestarclan",  
            "fadedarkforest",  
            "symbols",  
		"toxicplants",  
        \]:

`Now that we added the png, we can add our accessories. Scroll down until about line 555, #accessories.` 

`The accessories data placement doesn't really matter, but for organization and future updating, I am going to scroll down until after nyoncolours_data and add my own section - # Honey's mod`

`It isn't necessary, but when updating your mod it can be significantly faster if you comment where your additions are so you can just search for them later.`

        \# Honeys mod  
        toxicplants\_data \= \[  
            \["ARROWHEAD", "YUCCA"\],  
            \["LILIES", "STOCK"\],  
        \]

        for row, toxicplants in enumerate(toxicplants\_data):  
            for col, toxic in enumerate(toxicplants):  
                self.make\_group("toxicplants", (col, row), f"acc\_toxic{toxic}")

`The first part, toxicplants_data, is the data of the png. This is telling the game what accessories are within the file. Each grouping of brackets signifies a row` 

* `indentation doesn't matter here. It's for readability. I like it when it's horizontal instead of vertical, so it's really up to preference`

`The second part - I basically just copied another accessories code and replaced what was necessary (highlighted in blue)`

* **`toxicplants`** `is the name of the png - should be in three areas`  
* **`toxicplants_data`** `is essentially the accessories placement data. Should only be in one area`  
* **`toxic`** `is the type of accessory. It is to separate it from the others. Keep the name relevant to your accessories. Should be in two areas`  
* **`"acc_toxic"`** `is optional - you'll only edit this if you're adding a new accessory category. Otherwise, please use the existing categories ("acc_herbs", "acc_wild", "collars")`  
  * `(refer to "utility.py" if you want to add a category)`

#### **Pelts.py** {#pelts.py-4}

`Now we add the individual accessory names to the pelts.py! (scripts > cats) Scroll until around line 80, plant_accessories`

`If adding to an existing category:`

* `Make sure you're adding the accessories to a category that corresponds with the code you added to sprites.py!`   
  * `"acc_herbs" accessories goes to plant_accessories`  
  * `"acc_wild" accessories goes to wild_accessories`  
  * `"collars" accessories goes to collars`  
  * `Any accessory that covers the tail goes in tail_accessories (in this case, the accessory would be put in two different places)`

    plant\_accessories \= \["MAPLE LEAF", "HOLLY", "BLUE BERRIES", "FORGET ME NOTS", "RYE STALK", "CATTAIL", "POPPY", "ORANGE POPPY", "CYAN POPPY", "WHITE POPPY", "PINK POPPY",  
                        "BLUEBELLS", "LILY OF THE VALLEY", "SNAPDRAGON", "HERBS", "PETALS", "NETTLE", "HEATHER", "GORSE", "JUNIPER", "RASPBERRY", "LAVENDER",  
                        "OAK LEAVES", "CATMINT", "MAPLE SEED", "LAUREL", "BULB WHITE", "BULB YELLOW", "BULB ORANGE", "BULB PINK", "BULB BLUE", "CLOVER", "DAISY",  
                        "CLOVER", "DAISY", "LILY OF THE VALLEY", "HEATHER", "SNAPDRAGON", "GORSE", "BULB WHITE", "BULB YELLOW",  
                        "DRY HERBS", "DRY CATMINT", "DRY NETTLES", "DRY LAURELS", "ARROWHEAD", "YUCCA", "LILIES", "STOCK"  
                        \]

`If adding a new category:`  
*`Refer to the section "utility.py" when adding new categories`*

    plant\_accessories \= \["MAPLE LEAF", "HOLLY", "BLUE BERRIES", "FORGET ME NOTS", "RYE STALK", "CATTAIL", "POPPY", "ORANGE POPPY", "CYAN POPPY", "WHITE POPPY", "PINK POPPY",  
                        "BLUEBELLS", "LILY OF THE VALLEY", "SNAPDRAGON", "HERBS", "PETALS", "NETTLE", "HEATHER", "GORSE", "JUNIPER", "RASPBERRY", "LAVENDER",  
                        "OAK LEAVES", "CATMINT", "MAPLE SEED", "LAUREL", "BULB WHITE", "BULB YELLOW", "BULB ORANGE", "BULB PINK", "BULB BLUE", "CLOVER", "DAISY",  
                        "CLOVER", "DAISY", "LILY OF THE VALLEY", "HEATHER", "SNAPDRAGON", "GORSE", "BULB WHITE", "BULB YELLOW",  
                        "DRY HERBS", "DRY CATMINT", "DRY NETTLES", "DRY LAURELS"  
                        \]  
    toxic\_accessories \= \["ARROWHEAD", "YUCCA", "LILIES", "STOCK"\]  
    wild\_accessories \= \["RED FEATHERS", "BLUE FEATHERS", "JAY FEATHERS", "GULL FEATHERS", "SPARROW FEATHERS", "MOTH WINGS", "ROSY MOTH WINGS", "MORPHO BUTTERFLY", "MONARCH BUTTERFLY", "CICADA WINGS", "BLACK CICADA"\]

`Then scroll down def init_accessories and add your category to the below code`

        if acc\_display\_choice \== 1:  
            self.accessory \= choice(\[  
                choice(Pelt.plant\_accessories),  
                choice(Pelt.wild\_accessories),  
                choice(Pelt.toxic\_accessories),  
            \])  
        else:  
            self.accessory \= None

#### **Cats.py & scar\_events.py** {#cats.py-&-scar_events.py-1}

***`IF your accessory is a tail accessory`***`, follow these steps.`

`Navigate to cats.py (scripts folder > cats folder), scroll until line 2043, # remove accessories if need be`

`Here is the code that makes tail accessories invisible if a cat has a tail limb scar, such as no tail and half tail.`

        \# remove accessories if need be  
        if "NOTAIL" in self.pelt.scars and self.pelt.accessory in \[  
            "RED FEATHERS",  
            "BLUE FEATHERS",  
            "JAY FEATHERS",  
            "GULL FEATHERS",  
            "SPARROW FEATHERS",  
            "CLOVER",  
            "DAISY",  
		"ARROWHEAD",  
        \]:  
            self.pelt.accessory \= None  
        if "HALFTAIL" in self.pelt.scars and self.pelt.accessory in \[  
            "RED FEATHERS",  
            "BLUE FEATHERS",  
            "JAY FEATHERS",  
            "GULL FEATHERS",  
            "SPARROW FEATHERS",  
            "CLOVER",  
            "DAISY",  
		"ARROWHEAD",  
        \]:

`You want to do this, otherwise your tail accessory will be flying off kitties with no tails.`

`Theoretically if you want to, you can also add code for other no limb scars, like NOPAW, if your accessory relies on the area the no limb scar removes.`

`You'll also have to edit scar_events.py (scripts > events_module > scar_events) if you want to make sure tail accessories can't be generated for no tail kitties either.`

`Scroll until about line 153, if specialty in ["NOTAIL", "HALFTAIL"]. Add your tail accessories here.`

            specialty \= random.choice(scar\_pool)  
            if specialty in \["NOTAIL", "HALFTAIL"\]:  
                if cat.pelt.accessory in \["RED FEATHERS", "BLUE FEATHERS", "JAY FEATHERS", "GULL FEATHERS", "SPARROW FEATHERS", "CLOVER", "DAISY", "ARROWHEAD"\]:  
                    cat.pelt.accessory \= None

#### **Utility.py** {#utility.py}

`{scripts > utility.py}`

**`If you added a new category, edit utility!`**

`Okay so! IF you want to add a new category of accessories, you'll need to make sure to add it to the utility sprites pool.`

`Copy below:`

           `elif cat.pelt.accessory in cat.pelt.collars:`  
                `new_sprite.blit(`  
                    `sprites.sprites["collars" + cat.pelt.accessory + cat_sprite], (0, 0)`  
                `)`

`And only edit cat.pelt.collars and "collars" to fit your new accessory category.` 

* `cat.pelt.collars is the category listed in pelts.py.`  
  * `For me, this is toxic_accessories, so I'd just make it cat.pelt.collars -> cat.pelt.toxic_accessories`  
* `"collars" is the category listed in the accessories code within sprites.py`  
  * `For me, this is "acc_toxic", so I'd just make it "collars" -> "acc_toxic"`

        \# draw accessories  
        if not acc\_hidden:  
            if cat.pelt.accessory in cat.pelt.plant\_accessories:  
                new\_sprite.blit(  
                    sprites.sprites\["acc\_herbs" \+ cat.pelt.accessory \+ cat\_sprite\],  
                    (0, 0),  
                )  
            elif cat.pelt.accessory in cat.pelt.wild\_accessories:  
                new\_sprite.blit(  
                    sprites.sprites\["acc\_wild" \+ cat.pelt.accessory \+ cat\_sprite\],  
                    (0, 0),  
                )  
            elif cat.pelt.accessory in cat.pelt.collars:  
                new\_sprite.blit(  
                    sprites.sprites\["collars" \+ cat.pelt.accessory \+ cat\_sprite\], (0, 0)  
                )  
            elif cat.pelt.accessory in cat.pelt.toxic\_accessories:  
                new\_sprite.blit(  
                    sprites.sprites\["acc\_toxic" \+ cat.pelt.accessory \+ cat\_sprite\], (0, 0\)  
                )

`You can also go one step further and make a special accessory tag for your new category for accessory gain events, but I won't go over that since this is for art additions.`

* `Here's the files you might have to edit:`   
  * `handle_short_events.py: def handle_accessories`  
  * `test_handle_short_events.py: (???)`

#### **acc\_display.json** {#acc_display.json-1}

`(resources > dicts > acc_display.json)`

`This file holds all the text you see when the accessory is mentioned in an event or shown on a cat's profile.` 

`Scroll all the way down to the end of the file, and duplicate the code of the last text code. The "id" ("ARROWHEAD") should be exact to how the accessory is written in the .py files.`

 `"INFO": [`  
    `"default should be what you'd like to display on the cat profile",`  
    `"plural and singular will be used on events"`  
  `],`

  },  
  "INDIGONYLON": {  
    "default": "indigo nylon collar",  
    "plural": "indigo nylon collars",  
    "singular": "indigo nylon collar"  
  },  
  "ARROWHEAD": {  
    "default": "arrowhead",  
    "plural": "arrowheads",  
    "singular": "arrowhead"  
  }  
}

`Then boom, you're done! Run the game to make sure everything is working smoothly.`

# **Adding to White Patches** {#adding-to-white-patches}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`There are a whopping 130 white patches (2,730 individual sprites) currently in ClanGen, and there will likely be more official additions in the future.`

`"What's a white patch?" Basically, a lot of cats have patches of white on their pelts in a lot of unique patterns. You might be familiar with the term "tuxedo" where a cat has white on their chest. That's a white patch!`

***`The white patches PNG also holds the games vitiligo and colorpoint sprites.`*** `If you wish to add to that pool of sprites, you'll edit the whitepatches png!`

## **PNG** {#png-4}

`Making white patches is fairly easy - you're just drawing a pattern in pure white on a png! Use the layout files I provide (in the google drive link) in "layout" for your convenience.`

* `Make sure when you're done, you're deleting the background checker box pattern and lineart layer. Otherwise your sprites will look a little weird. Just a tad.`

**`NOTE`**`: If you want to do it ClanGen's way, here's the official documentation! It'll explain briefly how to draw the white patches in their style`

## **Coding** {#coding-5}

`Once you're happy with your white patches, replace and/or save the PNG. Make sure to write down somewhere the order of your additions, and if your additions are vitiligo/colorpoint. This is crucial later!`

`For my example, I'll be using "TAZ"!`

### **Sprites.py** {#sprites.py-5}

`{scripts > cats}`

`Scroll down until about 216 - #define white patches - this is the white patches list.` 

*`White patches, vitiligo, and color points all go into this list.`* `Vitiligo and color points are categories in pelts.py, which I'll go over later~`

`Here's how "TAZ" would be added to white_patches`

            \],  
            \[  
                "BULLSEYE",  
                "FINN",  
                "DIGIT",  
                "KROPKA",  
                "FCTWO",  
                "FCONE",  
                "MIA",  
                "SCAR",  
                "BUSTER",  
                "SMOKEY",  
                "HAWKBLAZE",  
                "CAKE",  
                "ROSINA",  
                "PRINCESS",  
            \],  
            \["LOCKET", "BLAZEMASK", "TEARS", "DOUGIE", "TAZ"\],  
        \]  
*`Adding TAZ to the last bracket category in white patches`*

            \[  
                "BULLSEYE",  
                "FINN",  
                "DIGIT",  
                "KROPKA",  
                "FCTWO",  
                "FCONE",  
                "MIA",  
                "SCAR",  
                "BUSTER",  
                "SMOKEY",  
                "HAWKBLAZE",  
                "CAKE",  
                "ROSINA",  
                "PRINCESS",  
            \],  
            \["LOCKET", "BLAZEMASK", "TEARS", "DOUGIE"\],  
            \["TAZ"\],  
        \]  
*`Adding TAZ to a new bracket. Only do this if you added a new row to the png`*

### **pelts.py** {#pelts.py-5}

`{scripts > cats}`

`Now, we're going to categorize your additions by how much they cover the pelt. There are 4 categories for white patches: little_white, mid_white, high_white, and mostly_white. Vitiligo and color patches don't go in these.`

`The way you interpret these categories is up to you. It's essentially just barely some white to covering the majority of the pelt.`

    mid\_white \= \['TUXEDO', 'FANCY', 'UNDERS', 'DAMIEN', 'SKUNK', 'MITAINE', 'SQUEAKS', 'STAR', 'WINGS',  
                 'DIVA', 'SAVANNAH', 'FADESPOTS', 'BEARD', 'DAPPLEPAW', 'TOPCOVER', 'WOODPECKER', 'MISS', 'BOWTIE',  
                 'VEST',  
                 'FADEBELLY', 'DIGIT', 'FCTWO', 'FCONE', 'MIA', 'ROSINA', 'PRINCESS', 'DOUGIE', 'TAZ'\]  
*`Example adding TAZ to mid_white`*

#### **Vit and Colorpoints** {#vit-and-colorpoints}

`Now that you added your additions to white_patches above, we're going to now add any white patches meant to be vitiligo or colorpoint to the categories in pelts.py.`

`Pretending "TAZ" is both of those, this is what the addition would look like:`

    point\_markings \= \['COLOURPOINT', 'RAGDOLL', 'SEPIAPOINT', 'MINKPOINT', 'SEALPOINT', 'TAZ'\]  
    vit \= \['VITILIGO', 'VITILIGOTWO', 'MOON', 'PHANTOM', 'KARPATI', 'POWDER', 'BLEACHED', 'SMOKEY', 'TAZ'\]

# **Adding to Tortie Pattern** {#adding-to-tortie-pattern}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`There is some confusion surrounding tortie patterns so I'll explain the gist of it here: Tortie patterns is a patch (similar to white patches) that make a cat a tortie upon generating.`

`It is drawn as white, then the game uses the pattern to "overlay" a second color and pelt type (if wild tortie) on the pelt. This allows the cat to have the bicolor look.`

`Tortie patterns have 43 options in the spritesheet. This is 86 individual sprites.`

## **PNG** {#png-5}

`Making tortie patches is fairly easy - you're just drawing a pattern in pure white on a png! Use the layout files I provide (in the google drive link) in "layout" for your convenience.`

* `Make sure when you're done, you're deleting the background checker box pattern and lineart layer. Otherwise your sprites will look a little weird. Just a tad.`

**`NOTE`**`: If you want to do it ClanGen's way, here's the official documentation! It'll explain briefly how to draw the white patches in their style, which can be used for tortie patches`

## **Coding** {#coding-6}

`Once you're happy with your torie patches, replace and/or save the PNG. Make sure to write down somewhere the order of your additions. This is crucial later!`

`For my example, I'll be using "TAZ"`

### **sprites.py** {#sprites.py-6}

`{scripts > cats} At about 398 is where you'll edit the file - define tortiepatchesmasks`

            \[  
                "ORIOLE",  
                "ROBIN",  
                "BRINDLE",  
                "PAIGE",  
                "ROSETAIL",  
                "SAFI",  
                "DAPPLENIGHT",  
                "BLANKET",  
                "BELOVED",  
                "BODY",  
            \],  
            \["SHILOH", "FRECKLED", "HEARTBEAT", "TAZ"\],  
        \]

`If you make a new row in the png, you'd make a new bracket section like below:`  
            \[  
                "ORIOLE",  
                "ROBIN",  
                "BRINDLE",  
                "PAIGE",  
                "ROSETAIL",  
                "SAFI",  
                "DAPPLENIGHT",  
                "BLANKET",  
                "BELOVED",  
                "BODY",  
            \],  
            \["SHILOH", "FRECKLED", "HEARTBEAT"\],  
		 \["TAZ"\],  
        \]

### **pelts.py** {#pelts.py-6}

`{scripts > cats} Now we add your additions to "tortiepatterns" in the pelts.py file. Like below:`

    tortiepatterns \= \['ONE', 'TWO', 'THREE', 'FOUR', 'REDTAIL', 'DELILAH', 'MINIMALONE', 'MINIMALTWO', 'MINIMALTHREE',  
                      'MINIMALFOUR', 'HALF',  
                      'OREO', 'SWOOP', 'MOTTLED', 'SIDEMASK', 'EYEDOT', 'BANDANA', 'PACMAN', 'STREAMSTRIKE', 'ORIOLE',  
                      'CHIMERA', 'DAUB', 'EMBER', 'BLANKET',  
                      'ROBIN', 'BRINDLE', 'PAIGE', 'ROSETAIL', 'SAFI', 'SMUDGED', 'DAPPLENIGHT', 'STREAK', 'MASK',  
                      'CHEST', 'ARMTAIL', 'SMOKE', 'GRUMPYFACE',  
                      'BRIE', 'BELOVED', 'BODY', 'SHILOH', 'FRECKLED', 'HEARTBEAT', 'TAZ'\]

`And you're done!`

# **Adding to Skins** {#adding-to-skins}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`Skins are 10 pixels max, and very easy to do unless you decide to be more complex with how they're created.`

`Because of the simplicity of the file, I don't think I need to explain how to create new skins. Please check out "layout" for the png files I recommend using while making new options!`

### **Expanding Canvases** {#expanding-canvases-2}

`You will need to expand the canvas size, as the existing skins already take all the space within the file. Here's how I do it with FireAlpaca:`

- `Navigate to the top and select "edit"`  
- `Select "canvas size..." (or ctrl + alt + c)`  
- `Specify top center since we're extending height`  
- `Add 350 x how many new rows you need`

`If your program doesn't work the way mine does, please consider searching up "how to expand canvas side in [art program]" in your browser`

## **Coding** {#coding-7}

`Once your skins are done and you're happy with how they look, replace the files in the sprites folder with your modified one. Or just save if you're editing the files directly.`

**`Make sure to delete the lineart and background layer when you're done!`** `Otherwise it might look a little strange in game. Just a tad.`

### **sprites.py** {#sprites.py-7}

`# Define skin colors`

### **pelts.py** {#pelts.py-7}

`skin_sprites`

# **Adding to Scars** {#adding-to-scars}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`This file is a doozy. Scars have` 

### **sprites.py** {#sprites.py-8}

`# Define scars`

### **pelts.py** {#pelts.py-8}

`# scars from other cats, other animals`

# **Adding to tints** {#adding-to-tints}

`Tints don't require the source version, unless it involves adding additional options elsewhere. The tints files are in your sprites > dicts folder.` 

# **Adding Symbols** {#adding-symbols}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`Symbols came with the leader's den feature in release 0.12.0. The symbols are reliant on prefixes that can be generated as clan names, aka the names.png file.`

# **Adding Camps** {#adding-camps}

***`Be aware you need the source (raw code) version of clangen to add additional options`***

`Yup, there sure is! Here's a brief run down`  
`* 8 pngs of your camp is required. Light mode and dark mode for each season. It's not required that they're different visually, but you need 8 separate pngs`  
`* Those pngs need to be named in a specific way: season_camp#_mode -- you'll need to add them to resources > images > camp_bg > desired biome (can also find examples in there as well)`  
`* Find the placements.json in the resources folder. If this is your first time doing UI placements, I recommend deliberately creating your camp with the same layout of an existing one so you can just copy paste the placements of an existing camp for your camp. If you do copy paste, simply change the UI's "ID" with "Biomecamp#", like "Beachcamp5"`  
```* From there, you will need to edit the makeclanscreen.py in your script > screens folder. This is where you add the button to the selection screen so your camp is available. Search ``def refresh_selected_camp``, scroll until you see the biome you want to add to (``self.biome_selected == "desired biome"``)  and add onto that section of code by simply copy and pasting what already exists, renaming the tab, and changing the tab number to 5```

           `tab_rect = ui_scale(pygame.Rect((0, 0), (80, 30)))`  
            `tab_rect.topright = ui_scale_offset((5, 5))`  
            `self.tabs["tab5"] = UISurfaceImageButton(`  
                `tab_rect,`  
                `"Slope",`  
                `get_button_dict(ButtonStyles.VERTICAL_TAB, (80, 30)),`  
                `object_id="@buttonstyles_vertical_tab",`  
                `manager=MANAGER,`  
                `anchors={`  
                    `"right": "right",`  
                    `"right_target": self.elements["art_frame"],`  
                    `"top_target": self.tabs["tab4"],`  
                `},`  
            `)`

```* After that's done, you'll likely have to add a new self.tab line for tab5 (search ``self.tabs["tab4"]``). It'll look something like:```

       `self.tabs["tab5"].disable() if self.selected_camp_tab == 5 else self.tabs[`  
            `"tab5"`  
        `].enable()`

`That should be everything you need to do. Hopefully I explained this well enough` 

# **Adding Patrol Art** {#adding-patrol-art}

`Very simple! Make art, add to resources > images > patrol art. Find the patrol you want to add the art to in the game files, add patrol art name (without .png) in the art area.`

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,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>