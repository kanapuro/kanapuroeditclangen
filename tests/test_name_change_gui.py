def test_suffix_applied_to_single_name():
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from scripts.clan import Clan
    from scripts.cat.cats import Cat
    from scripts.game_structure.game_essentials import game

    # Create clan configured to prefer single names
    c = Clan(name='TestClan')
    c.clan_settings['warrior_names'] = False
    c.clan_settings['ancient_names'] = False
    c.clan_settings['single_names'] = True
    c.clan_settings['syllable_names'] = False
    game.clan = c

    # Create a new cat (auto-generated single name expected)
    cat = Cat()
    Cat.all_cats[cat.ID] = cat
    Cat.all_cats_list.append(cat)

    assert cat.name.name_type in ('single', 'syllable')

    # Simulate ChangeCatName.save behavior
    raw_suffix = 'heart'
    if raw_suffix.strip() != '' and cat.name.name_type in ('single', 'syllable'):
        cat.name.name_type = 'warrior'
    cat.name.suffix = raw_suffix

    assert cat.name.name_type == 'warrior'
    assert raw_suffix in str(cat.name)
