from django.db import models
from django.core.exceptions import ValidationError
import re

# TODO : Allow spaces in patterns (["v1":"DV1" | "v2":"DV2"])

def preset_pr_validator(preset):
    """
        The validator of the processing_rules field of SearchPreset.
        Check the field is correctly formated.
        
        Expected format :
        DISPLAY "Displayed label":"key"
        "key" "Displayed label":["value1":"Display value 1"|"value2":"Other displayed value"]
        
        Example :
        DISPLAY "Site web":"website"
        "fee" "Payant":["yes":"Oui"|"no":"Non"]
        
        The star '*' is also supported to take all the others values.
        Example :
        "fee" "Payant":["yes":"Oui"|"no":"Non"|"*":"Inconnu"]
    """
    i = 1
    for line in preset.splitlines():
        if line.startswith("DISPLAY"):
            if re.match('DISPLAY "[\w ]+":"\w+"', line):
                i += 1
                continue
            else:
                raise ValidationError("Erreur ligne {}. Le label et la clé doivent être entourés de guillemets (\") et séparés par deux points (:)".format(i))
        elif not re.match('"\w+" ".*":\[".*":".*"(\|".*":".*")*\]', line):
            raise ValidationError("Erreur ligne {}. Cette ligne ne correspond à aucun pattern valable".format(i))
        
        try:
            key = line.split()[0]
            action = line.split(' ', 1)[1]
        except IndexError:
            raise ValidationError("Erreur ligne {}. La clé et l'action doivent être séparés par une espace.".format(i))
        if not re.search('".*"', key):
            raise ValidationError("Erreur ligne {}. La clé est invalide.".format(i))
        if not re.search('".*":\["\w+":".*"(\|"\w+":".*")*\]', action):
            raise ValidationError("Erreur ligne {}. L'action est invalide.".format(i))
        i += 1
    return

def osm_keys_validator(field):
    i = 1
    for line in field.splitlines():
        if re.match('"\w+"="\w+"', line):
            continue
        else:
            raise ValidationError('Erreur ligne {}. Chaque ligne doit être de la forme \'"key"="value"\'.'.format(i))
        i += 1
    return

class SearchPreset(models.Model):
    """
        A search preset with all the stuff needed to display it nicely.
        
        If processing_rules is blank, only address is displayed.
    """
    name = models.CharField(max_length=50)
    osm_keys = models.TextField(
        blank=True, null=True, validators=[osm_keys_validator]
    )
    processing_rules = models.TextField(
        blank=True, null=True,
        validators=[preset_pr_validator]
    )
    
    def render_pr(self, properties):
        """
            Return a string describing the object with its properties and PR.
        """
        output = []
        for line in self.processing_rules.splitlines():
            if re.match('DISPLAY ".*":"\w+"', line):
                label, key = re.findall('DISPLAY "(.*)":"(\w+)"', line)[0]
                value = properties.get(key)
                if not value:
                    continue
                else:
                    output.append("{} : {}".format(label, value))
                    continue
            if re.match('"\w+" ".*":\[".*":".*"(\|".*":".*")*\]', line):
                key = re.findall('"(\w+)"', line)[0]
                values = properties.get(key)
                if not values:
                    continue
                else:
                    label = re.search('\w+', line.split()[1]).group()
                    possible_values = re.findall('"(\w+|\*)":"', line.split(' ', 1)[1])
                    displayed_values = re.findall('":"([\w ]+)"', line.split(' ', 1)[1])
                    values_list = values.split(';')
                    values_output_list = []
                    for value in [i for i in values_list if i in possible_values]:
                        values_output_list.append(displayed_values[possible_values.index(value)])
                    if '*' in possible_values:
                        values_output_list.append(displayed_values[possible_values.index('*')])
                    if not values_output_list:
                        continue
                    else:
                        output.append("{} : {}".format(label,
                            ' - '.join(values_output_list)))
                        continue
        return '\n'.join(output)
    
    def __str__(self):
        return self.name
