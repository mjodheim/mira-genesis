using Domain.Enums;

namespace Domain
{
    /// <summary>
    /// Formulation d'une recette : combien de malt (ou de miel), de houblon, de levure et d'eau
    /// pour atteindre un volume et une densité cible.
    /// <para>
    /// Un modèle de langage sait décrire un style, mais il ne SAIT PAS mettre à l'échelle : il
    /// propose la même « 5 kg de malt, 50 g de houblon » pour 20 L que pour 200 L, ou 3 kg de
    /// miel là où il en faut 6. Ces quantités-là se calculent — elles ne s'inventent pas.
    /// </para>
    /// </summary>
    public static class RecipeMath
    {
        /// <summary>Rendement de brassage usuel en petite brasserie (grain → moût).</summary>
        public const decimal DefaultEfficiency = 72m;

        /// <summary>Atténuation apparente usuelle d'une levure de fermentation haute.</summary>
        public const decimal DefaultAttenuation = 75m;

        public const int DefaultBoilMinutes = 60;

        /// <summary>Densité en points (1.050 → 50).</summary>
        public static decimal GravityPoints(decimal specificGravity) =>
            Math.Round((specificGravity - 1m) * 1000m, 1);

        /// <summary>
        /// Extrait apporté par un fermentescible, en points × litres par kilogramme (à 100 %).
        /// 0 pour ce qui n'apporte pas de sucre (houblon, levure, eau, épices).
        /// </summary>
        public static decimal ExtractYield(IngredientType type) => type switch
        {
            IngredientType.Grain => 300m,   // malt de base, mouture fine
            IngredientType.Honey => 340m,   // miel, ~80 % de sucres fermentescibles
            IngredientType.Adjunct => 385m, // sucres et sirops
            IngredientType.Fruit => 60m,    // les fruits sont surtout de l'eau
            _ => 0m,
        };

        /// <summary>
        /// Vrai si le rendement de brassage s'applique. Le grain doit être empâté (on n'en
        /// extrait que ~72 %) ; le miel et le sucre se dissolvent intégralement — leur appliquer
        /// un rendement ferait sous-doser un hydromel de près de 30 %.
        /// </summary>
        public static bool NeedsMashing(IngredientType type) => type == IngredientType.Grain;

        /// <summary>
        /// Masse (kg) d'un fermentescible pour apporter <paramref name="gravityPoints"/> points
        /// sur <paramref name="volumeLiters"/> litres.
        /// </summary>
        public static decimal FermentableKg(decimal gravityPoints, decimal volumeLiters, IngredientType type, decimal efficiencyPercent)
        {
            decimal yield = ExtractYield(type);
            if (yield <= 0m)
                throw new ArgumentException($"{type} n'apporte pas de sucre : il ne peut pas servir à atteindre la densité cible.");

            decimal efficiency = NeedsMashing(type) ? efficiencyPercent / 100m : 1m;
            if (efficiency <= 0m) throw new ArgumentOutOfRangeException(nameof(efficiencyPercent));

            return Math.Round(gravityPoints * volumeLiters / (yield * efficiency), 3);
        }

        /// <summary>
        /// Taux d'utilisation du houblon (formule de Tinseth) : il chute quand le moût est dense
        /// et croît avec la durée d'ébullition. C'est ce qui fait qu'une même dose donne
        /// 35 IBU dans une blonde et 25 dans une triple.
        /// </summary>
        public static decimal HopUtilization(decimal originalGravity, int boilMinutes)
        {
            if (boilMinutes <= 0) return 0m;
            double og = (double)originalGravity;
            double bigness = 1.65 * Math.Pow(0.000125, og - 1.0);
            double boilTime = (1.0 - Math.Exp(-0.04 * boilMinutes)) / 4.15;
            double utilization = bigness * boilTime;
            return utilization <= 0 ? 0m : Math.Round((decimal)utilization, 5);
        }

        /// <summary>Masse de houblon (g) pour atteindre une amertume donnée.</summary>
        public static decimal HopGrams(decimal ibu, decimal volumeLiters, decimal alphaAcidPercent, decimal originalGravity, int boilMinutes)
        {
            decimal utilization = HopUtilization(originalGravity, boilMinutes);
            if (utilization <= 0m || alphaAcidPercent <= 0m) return 0m;
            return Math.Round(ibu * volumeLiters / (utilization * (alphaAcidPercent / 100m) * 1000m), 1);
        }

        /// <summary>Amertume (IBU) apportée par une masse de houblon donnée.</summary>
        public static decimal IbuFromHops(decimal grams, decimal volumeLiters, decimal alphaAcidPercent, decimal originalGravity, int boilMinutes)
        {
            if (volumeLiters <= 0m) return 0m;
            decimal utilization = HopUtilization(originalGravity, boilMinutes);
            return Math.Round(utilization * (alphaAcidPercent / 100m) * grams * 1000m / volumeLiters, 1);
        }

        /// <summary>Densité finale estimée depuis l'atténuation apparente de la levure.</summary>
        public static decimal EstimateFinalGravity(decimal originalGravity, decimal attenuationPercent) =>
            Math.Round(1m + (originalGravity - 1m) * (1m - attenuationPercent / 100m), 3);

        /// <summary>Levure sèche (g) : ~0,5 g/L, doublé au-delà de 1.060 (moût dense = plus de cellules).</summary>
        public static decimal DryYeastGrams(decimal volumeLiters, decimal originalGravity) =>
            Math.Round(volumeLiters * (originalGravity >= 1.060m ? 1m : 0.5m), 0);

        /// <summary>
        /// Eau totale (L) : volume final + absorption du grain (≈ 1 L/kg) + évaporation
        /// (≈ 10 %/h d'ébullition) + pertes au fond de cuve (≈ 4 %).
        /// </summary>
        public static decimal TotalWaterLiters(decimal volumeLiters, decimal grainKg, int boilMinutes) =>
            Math.Round(volumeLiters
                       + grainKg
                       + volumeLiters * 0.10m * boilMinutes / 60m
                       + volumeLiters * 0.04m, 1);

        // ---- Garde-fou de vraisemblance -----------------------------------------

        /// <summary>
        /// Fourchette plausible d'un ingrédient, en GRAMMES PAR LITRE de moût (1 L ≈ 1 kg pour
        /// les liquides). Volontairement très large — dix fois plus permissive que la pratique
        /// courante : elle n'est là que pour arrêter l'aberration (50 kg de malt dans 20 L,
        /// 2 kg de houblon dans un fût), pas pour dicter une recette.
        /// <c>null</c> = pas de contrôle (eau, divers).
        /// </summary>
        public static (decimal Min, decimal Max)? PlausibleGramsPerLiter(IngredientType type) => type switch
        {
            IngredientType.Grain => (20m, 600m),      // usuel : 150–350 g/L
            IngredientType.Honey => (20m, 600m),      // usuel : 250–350 g/L
            IngredientType.Adjunct => (0.5m, 500m),
            IngredientType.Fruit => (10m, 2000m),     // une bière aux fruits peut dépasser 1 kg/L
            IngredientType.Hop => (0.05m, 40m),       // usuel : 1–5 g/L, jusqu'à ~25 en NEIPA
            IngredientType.Yeast => (0.05m, 20m),     // usuel : 0,5–1 g/L en levure sèche
            IngredientType.Spice => (0.005m, 10m),
            _ => null,                                // Water, Other : aucun ordre de grandeur
        };

        /// <summary>Convertit une quantité en grammes (1 L ≈ 1 kg, convention de l'application).</summary>
        public static decimal ToGrams(decimal quantity, Unit unit) => unit switch
        {
            Unit.Kilogram => quantity * 1000m,
            Unit.Gram => quantity,
            Unit.Milligram => quantity / 1000m,
            Unit.Liter => quantity * 1000m,
            Unit.Milliliter => quantity,
            _ => quantity,
        };

        /// <summary>
        /// Vérifie qu'une quantité a un ordre de grandeur possible pour le volume brassé.
        /// Renvoie <c>null</c> si tout va bien, sinon la raison (destinée au modèle).
        /// </summary>
        public static string? ImplausibleQuantity(IngredientType type, decimal quantity, Unit unit, decimal batchVolumeLiters)
        {
            if (batchVolumeLiters <= 0m) return null;
            if (PlausibleGramsPerLiter(type) is not var (min, max)) return null;

            decimal perLiter = ToGrams(quantity, unit) / batchVolumeLiters;
            if (perLiter >= min && perLiter <= max) return null;

            return $"Quantité invraisemblable : {quantity} {unit} de {type} pour {batchVolumeLiters} L, " +
                   $"soit {Math.Round(perLiter, 3)} g/L, alors qu'on attend entre {min} et {max} g/L. " +
                   "Recalcule la quantité avec plan_recipe avant de réessayer.";
        }
    }
}
