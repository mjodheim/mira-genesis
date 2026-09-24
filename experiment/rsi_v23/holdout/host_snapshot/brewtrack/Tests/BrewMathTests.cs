using Domain;

namespace BrewTrack.Tests;

/// <summary>Calculs de brassage : degrés Plato et droits d'accise.</summary>
public class BrewMathTests
{
    [Fact]
    public void PlatoFromGravity_returns_zero_at_or_below_water()
    {
        Assert.Equal(0m, BrewMath.PlatoFromGravity(1.000m));
        Assert.Equal(0m, BrewMath.PlatoFromGravity(0.999m));
    }

    [Theory]
    [InlineData(1.040, 9.5, 10.5)]
    [InlineData(1.050, 12.0, 12.8)]
    [InlineData(1.060, 14.5, 15.2)]
    public void PlatoFromGravity_matches_known_ranges(double sg, double lo, double hi)
    {
        decimal p = BrewMath.PlatoFromGravity((decimal)sg);
        Assert.InRange(p, (decimal)lo, (decimal)hi);
    }

    [Fact]
    public void ExciseDuty_is_rate_times_hectoliters_times_plato()
    {
        // 200 L = 2 hL, à 1.050 (~12.4 °P), taux 1,00 → ≈ 2 × 12.4 × 1.
        decimal plato = BrewMath.PlatoFromGravity(1.050m);
        decimal expected = Math.Round(2m * plato * 1.00m, 2);
        Assert.Equal(expected, BrewMath.ExciseDuty(200m, 1.050m, 1.00m));
    }

    [Fact]
    public void ExciseDuty_scales_with_volume_and_rate()
    {
        decimal one = BrewMath.ExciseDuty(100m, 1.050m, 2.00m);
        decimal twice = BrewMath.ExciseDuty(200m, 1.050m, 2.00m);
        Assert.Equal(Math.Round(one * 2m, 2), twice);
        Assert.Equal(0m, BrewMath.ExciseDuty(200m, 1.050m, 0m));
    }
}
