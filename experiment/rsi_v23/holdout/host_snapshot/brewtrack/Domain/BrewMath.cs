namespace Domain
{
    /// <summary>Calculs de brassage partagés (densité, degrés Plato, accises).</summary>
    public static class BrewMath
    {
        /// <summary>
        /// Convertit une densité (gravité spécifique, ex. 1.050) en degrés Plato via la
        /// formule polynomiale usuelle. Renvoie 0 pour une densité ≤ 1.
        /// </summary>
        public static decimal PlatoFromGravity(decimal sg)
        {
            if (sg <= 1m) return 0m;
            double g = (double)sg;
            double plato = -616.868 + 1111.14 * g - 630.272 * g * g + 135.997 * g * g * g;
            return plato < 0 ? 0m : Math.Round((decimal)plato, 2);
        }

        /// <summary>Titre alcoométrique (% vol.) depuis les densités initiale et finale.</summary>
        public static decimal AbvFromGravities(decimal originalGravity, decimal finalGravity) =>
            Math.Round((originalGravity - finalGravity) * 131.25m, 2);

        /// <summary>
        /// Droit d'accise (bière) sur une quantité, selon le barème au litre-hectolitre par
        /// degré Plato : duty = taux × hectolitres × °Plato.
        /// </summary>
        public static decimal ExciseDuty(decimal volumeLiters, decimal originalGravity, decimal dutyPerHlPerPlato)
        {
            decimal hl = volumeLiters / 100m;
            decimal plato = PlatoFromGravity(originalGravity);
            return Math.Round(hl * plato * dutyPerHlPerPlato, 2);
        }
    }
}
