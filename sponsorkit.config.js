import { defineConfig, tierPresets } from 'sponsorkit'

export default defineConfig({
    // Providers configs
    github: {
        login: 'Chizer77',
        type: 'user',
    },
    afdian: {
        // ...
        userId: 'f6bca0fc272711f0aace52540025c377',
        exechangeRate: 7,
        includePurchases: true,
        purchaseEffectivity: 30,
    },

    // Rendering configs
    width: 800,
    renderer: 'tiers', // or 'circles'
    formats: ['json', 'svg', 'png', 'webp'],
    tiers: [
        // // Past sponsors, currently only supports GitHub
        // {
        //     title: 'Past Sponsors',
        //     monthlyDollars: -1,
        //     preset: tierPresets.xs,
        // },
        // Default tier
        {
            title: 'Backers',
            preset: tierPresets.base,
        },
        {
            title: 'Sponsors',
            monthlyDollars: 10,
            preset: tierPresets.medium,
        },
        {
            title: 'Silver Sponsors',
            monthlyDollars: 50,
            preset: tierPresets.large,
        },
        {
            title: 'Gold Sponsors',
            monthlyDollars: 100,
            preset: tierPresets.xl,
        },
    ],
})