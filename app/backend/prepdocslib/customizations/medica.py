from azure.search.documents.indexes.models import SimpleField

class FieldCustomizer:
    """
    Concrete parser that can parse CSV into Page objects. Each row becomes a Page object.
    """

def append_fields(fields: list) -> list:
    """
    Appends custom fields to the given list of fields.
    
    Args:
        fields (list): The list of fields to append to.
    
    Returns:
        list: The updated list of fields with custom fields appended.
    """
    fields.append(SimpleField(name="planid", type="Edm.String", filterable=True, facetable=False))
    fields.append(SimpleField(name="doctype", type="Edm.String", filterable=True, facetable=False))
    fields.append(SimpleField(name="locale", type="Edm.String", filterable=True, facetable=True))
    
    return fields