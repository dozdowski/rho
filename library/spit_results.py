#
# Copyright (c) 2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

# pylint: disable=R0903

"""Module responsible for displaying results of rho report"""

import csv
import os
from ansible.module_utils.basic import AnsibleModule


class Results(object):
    """The class Results contains the functionality to parse
    data passed in from the playbook and to output it in the
    csv format in the file path specified.
    """

    def __init__(self, module):
        self.module = module
        self.name = module.params['name']
        self.file_path = module.params['file_path']
        self.all_vars = module.params['all_vars']
        self.desired_facts = module.params['desired_facts']

    def write_to_csv(self):
        """Output report data to file in csv format"""

        # The results come in two parts. Results from the single
        # Ansible module which includes all of Rho's Python modules
        # appear in all_vars['res']. Other results appear as other
        # keys in all_vars. To avoid printing extra Ansible
        # information, we only output data that is known to come from
        # Rho unless the user requests it via 'desired_facts':

        # Keys that appear in 'res' objects
        res_keys = set()
        # Keys that appear in the top-level host vars
        other_keys = set()

        # Flatten the data and update res_keys and other_keys
        flat_vars = {}
        for host, data in self.all_vars.iteritems():
            # Need to update the keys with every host's set in
            # case some commands failed on some hosts but not
            # others.
            res_keys.update(data['res'].keys())

            # flat_data is a dictionary in which all of the facts
            # we want to output are keys, and their values are the
            # corresponding values in the dict.
            flat_data = data.copy()
            del flat_data['res']
            other_keys.update(flat_data.keys())

            flat_data.update(data['res'])
            flat_vars[host] = flat_data

        # We know a key came from Rho if either it was in a 'res'
        # attribute or it starts with 'rho'. If we don't know it's
        # from Rho, we default to not printing it, because some
        # Ansible keys contain information users probably wouldn't
        # want to release accidentally (like the path to their SSH
        # key). They can always override this by setting
        # 'desired_facts'.
        if self.desired_facts != ['default']:
            keys = set(self.desired_facts)
        else:
            keys = res_keys
            for key in list(other_keys):
                if key.startswith('rho'):
                    keys.add(key)

        # Filter the data to only what we want. This is not
        # necessary just for writing the CSV, but we also output
        # this information as an Ansible variable.
        filtered_vars = {host:
                         {fact: value
                          for (fact, value) in flat_data.iteritems()
                          if fact in keys}
                         for host, flat_data in flat_vars.iteritems()}

        normalized_path = os.path.normpath(self.file_path)
        with open(normalized_path, 'w') as write_file:
            # Construct the CSV writer
            writer = csv.DictWriter(write_file, sorted(keys),
                                    extrasaction='ignore', delimiter=',')

            # Write a CSV header if necessary
            file_size = os.path.getsize(normalized_path)
            if file_size == 0:
                writer.writeheader()

            # Write the data
            for data in filtered_vars.itervalues():
                writer.writerow(data)

        # Save the data for our results
        # pylint: disable=attribute-defined-outside-init
        self.filtered_vars = filtered_vars
        self.keys = list(keys)


def main():
    """Function to trigger collection of results and write
    them to csv file
    """

    fields = {
        "name": {"required": True, "type": "str"},
        "file_path": {"required": True, "type": "str"},
        "all_vars": {"required": True, "type": "dict"},
        "desired_facts": {"required": True, "type": "list"}
    }

    module = AnsibleModule(argument_spec=fields)

    results = Results(module=module)
    results.write_to_csv()
    module.exit_json(changed=False,
                     meta={'filtered_vars': results.filtered_vars,
                           'keys': results.keys})


if __name__ == '__main__':
    main()
