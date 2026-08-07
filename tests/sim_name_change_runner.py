import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.game_structure.game_essentials import game
from scripts.clan import Clan
from scripts.cat.cats import Cat

# Create and attach a test clan with settings favoring single names
c = Clan(name='TestClan')
# Force clan settings to only allow single names for this test
c.clan_settings['warrior_names'] = False
c.clan_settings['ancient_names'] = False
c.clan_settings['single_names'] = True
c.clan_settings['syllable_names'] = False

game.clan = c

# Create a new cat (will auto-generate a single name)
cat = Cat()
# Ensure cat is added to global registry for name detection if needed
Cat.all_cats[cat.ID] = cat
Cat.all_cats_list.append(cat)

print('Initial name_type:', cat.name.name_type)
print('Initial printed name:', str(cat.name))

# Simulate user entering a suffix in ChangeCatName window
raw_suffix = 'heart'
# Simulate the save logic we patched: if raw_suffix non-empty and name_type in single/syllable, set to warrior
if raw_suffix.strip() != '' and cat.name.name_type in ('single','syllable'):
    cat.name.name_type = 'warrior'
cat.name.suffix = raw_suffix

print('After change name_type:', cat.name.name_type)
print('After change printed name:', str(cat.name))
