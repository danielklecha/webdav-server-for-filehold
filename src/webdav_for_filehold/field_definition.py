import copy
from typing import Any, Dict


class FieldDefinition:
    """
    Defines default structures for FileHold field definitions and display formats.
    """

    default_display_format: Dict[str, Any] = {
        'DecimalPlaces': 0,
        'DecimalSeparator': '.',
        'GroupSeparator': ',',
        'CurrencySymbolAtBeginning': False,
        'DateTimeFormat': 'ShortDate',
        'DateOrNegativeFormat': '',
        'NegativeColor': '',
        'Rows': 0,
        'ShowFullPath': False,
        'PathSeparator': '\\\\'
    }

    default_field_def: Dict[str, Any] = {
        'MetadataFieldId': 0,
        'MetadataHeaderText': '',
        'ColumnIndex': 0,
        'IsSystem': False,
        'Description': '',
        'Type': 'Text',
        'IsDatabaseLookup': False,
        'SystemFieldId': 0,
        'AllowEdit': False,
        'AllowMultiselection': False,
        'MinCharCount': 0,
        'MaxCharCount': 0,
        'CurrencySymbol': '',
        'SelectOnlyLeaves': False,
        'MinValue': None,
        'MaxValue': None,
        'InitialValue': None,
        'Caption': '',
        'DisplayFormat': default_display_format,
        'IsHighlighted': False,
        'IsFilterContains': False,
        'RequiredInSchemas': None,
        'NotRequiredInSchemas': None,
        'ReadOnlyInSchemas': None,
        'ClearAtCheckInInSchemas': None
    }

    @staticmethod
    def make_field(overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new field definition dictionary by merging the defaults with the provided overrides.

        Uses deepcopy to ensure that nested dictionaries (like DisplayFormat) in the
        default definition are not modified by subsequent changes to the returned dictionary.

        Args:
            overrides: A dictionary containing the keys and values to override
                       in the default field definition.

        Returns:
            A new dictionary with the merged field definition.
        """
        # copy.deepcopy is essential here because default_field_def contains
        # a mutable dictionary (DisplayFormat). A shallow copy would share the reference,
        # leading to potential side effects if the result is modified.
        field_def = copy.deepcopy(FieldDefinition.default_field_def)
        field_def.update(overrides)
        return field_def
