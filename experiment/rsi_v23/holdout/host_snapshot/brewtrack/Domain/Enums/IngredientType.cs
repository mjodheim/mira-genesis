namespace Domain.Enums
{
    public enum IngredientType
    {
        Grain,
        Hop,
        Yeast,
        Fruit,
        Honey,
        Adjunct,
        Water,
        Other,
        // Ajouté en fin d'énumération : le type est persisté en entier (integer),
        // insérer ailleurs décalerait les valeurs déjà en base.
        Spice
    }
}
