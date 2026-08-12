"use client";

import dynamic from "next/dynamic";
import { Swords } from "lucide-react";

const Earth3D = dynamic(() => import("@/components/Earth3D"), {
  ssr: false,
  loading: () => <div className="absolute inset-0 w-full h-full bg-background/50 animate-pulse rounded-full" />,
});
const StartDashboard = dynamic(() => import("@/components/StartDashboard"), { ssr: false });



export default function Home() {
  return (
    <div className="flex min-h-screen h-screen w-full bg-background overflow-y-auto lg:overflow-hidden">

      {/* Main Content */}
      <div className="flex flex-1 flex-col">

        {/* Main Grid */}
        <main className="flex flex-col lg:flex-row flex-1 gap-4 sm:gap-6 px-4 sm:px-6 lg:px-8 pb-6 sm:pb-8">
          {/* Left Section - Hero */}
          <div className="flex-1 min-w-0 relative flex flex-col pt-[50px] sm:pt-[60px] lg:pt-[60px]">

            {/* Earth Visualization */}
            <div className="relative h-[55vh] sm:h-[60vh] lg:flex-1 lg:h-auto w-full flex items-center justify-center -mt-[10px] sm:-mt-[30px] lg:-mt-[38px]">
              <Earth3D />

              {/* Left overlay cards */}
              <div className="absolute bottom-2 left-2 sm:bottom-6 sm:left-6 z-10 max-w-[220px] sm:max-w-[320px] flex flex-col gap-2 sm:gap-3">
                {/* Agentic Arena Card */}
                <div className="glass-card p-3 sm:p-6 flex flex-col gap-1.5 sm:gap-3 backdrop-blur-xl border-[#412AD1]/20 bg-[#FFFFFF]/80">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className="p-1 sm:p-2 rounded-full bg-[#412AD1]/10 text-[#412AD1] animate-pulse">
                      <Swords className="h-3.5 w-3.5 sm:h-5 sm:w-5" />
                    </div>
                    <span className="text-[10px] sm:text-sm font-semibold text-[#292524] tracking-wide">Bittensor Arena</span>
                  </div>
                  <p className="text-[10px] sm:text-sm text-[#292524]/80 leading-relaxed">
                    Discover the Bittensor network. Explore subnet categories, compare incentives and performance, and uncover the best networks in <span className="text-[#292524] font-medium">Compute</span>, <span className="text-[#292524] font-medium">AI Agents</span>, <span className="text-[#292524] font-medium">Trading</span>, <span className="text-[#292524] font-medium">security</span> & more.
                  </p>
                </div>

                {/* Galileo Tribute Card */}
                <div className="hidden sm:block select-none text-right">
                  <div className="glass-card p-5 rounded-2xl bg-[#FFFFFF]/85 backdrop-blur-xl border border-[#292524]/10 flex flex-col items-end gap-3 shadow-lg relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-[#412AD1]/5 via-transparent to-[#B50BBB]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>

                    <p className="text-sm text-[#292524] font-serif leading-relaxed text-right z-10">
                      Intelligence belongs to no one. <span className="text-[#412AD1] font-semibold">Markets</span> discover value, <span className="text-[#412AD1] font-semibold">subnets</span> create it, and <span className="text-[#412AD1] font-semibold font-serif italic">TAO</span> rewards it.
                    </p>

                    <div className="mt-1 opacity-90 z-10 relative">
                      <div className="absolute -inset-4 bg-gradient-to-r from-transparent via-[#292524]/5 to-transparent blur-xl -skew-x-12 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"></div>
                      <span className="font-sans font-medium text-[13px] sm:text-sm text-[#412AD1] block tracking-wide">
                        Const, core dev @ Rao Foundation
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Section - Analytics Dashboard */}
          <div className="w-full lg:flex-1 flex flex-col relative min-h-[300px] sm:min-h-[400px]">
            <StartDashboard />
          </div>
        </main>
      </div>
    </div>
  );
}
