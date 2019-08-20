// @flow
import React from "react"
import { connect } from "react-redux"

import WithDrawer from "./WithDrawer"

class TermsPage extends React.Component<*, void> {
  render() {
    return (
      <WithDrawer>
        <div className="collection-list-content">
          <div className="card centered-content">
            <h2 className="mdc-typography--title terms-title">
              Terms of Service
            </h2>
            <div className="terms-of-service">
              <div className="terms-update">
                Last update on January 10, 2018
              </div>
              <h3 className="terms-subheading">Summary</h3>
              <ul className="terms-list">
                <li>
                  <span className="terms-strong">
                    Accept these terms to use this website.{" "}
                  </span>
                  If the following Terms of Use are not accepted in full, you do
                  not have permission to access the contents of this site or to
                  upload content to this site.
                </li>
                <li>
                  <span className="terms-strong">
                    No permanent availability of video streams.{" "}
                  </span>
                  If no one has viewed your video in the last 2 years, we may
                  remove it from the site. If and when we remove a video, we
                  will alert you and you may request that we continue to make it
                  available. We will do our best to accommodate these requests,
                  resources permitting.
                </li>
                <li>
                  <span className="terms-strong">
                    No permanent storage of video.{" "}
                  </span>
                  We will store your source video for at least 6 years. Even if
                  your video is removed from active streaming (see above), it
                  will be archived for up to 6 years. You may download the
                  source video (to dropbox) at any time during those 6 years.
                  After that term, we will no longer be able to guarantee that
                  you can download your video and we may require extra time and
                  a fee in order to download the source video.
                </li>
                <li>
                  <span className="terms-strong">No Moderators. </span>
                  Content uploaded to ODL Video is not moderated. If a user
                  alerts us to a video that violates the terms of service, and
                  we determine that it does, it will be removed from the site.
                </li>
                <li>
                  <span className="terms-strong">Your work is yours. </span>
                  Those who upload to ODL Video retain the rights to their own
                  work while giving us the right to distribute their video until
                  and unless they delete it from our website.
                </li>
                <li>
                  <span className="terms-strong">
                    Others' work is NOT yours.{" "}
                  </span>
                  Unauthorized use of someone else's content -- including music,
                  video, images and other media -- in your uploads is theft and
                  will not be tolerated on ODL Video. Users should abide by{" "}
                  <a
                    target="_blank"
                    rel="noopener noreferrer"
                    href="http://web.mit.edu/copyright/"
                  >
                    MIT's copyright guidelines
                  </a>
                  .
                </li>
                <li>
                  <span className="terms-strong">
                    Think someone used your work without permission?{" "}
                  </span>
                  If you believe that any of your intellectual property rights
                  have been violated by material available on ODL Video, contact
                  us at{" "}
                  <a href="mailto:odl-video-support@mit.edu">
                    odl-video-support@mit.edu
                  </a>
                  .
                </li>
              </ul>
              <h3 className="terms-subheading">User Obligation</h3>
              <div className="terms-div">
                If you are seeking to upload material to this site or to engage
                in any activities within the ODL Video website (hereafter
                referred to as "the site" or ODL Video) other than passively
                viewing site content, you must register and become a site
                member. As part of the registration process, you will be asked
                to ACCEPT these Terms of Use. On doing so, you will be deemed to
                have consented to and you will be bound by these Terms of Use.
              </div>
              <div className="terms-div">
                Visitors to the site merely wishing to view content do not need
                to register and become members. However, any use of this site
                (which includes but is not limited to simply viewing the sites
                content) constitutes your acknowledgment and acceptance of these
                Terms of Use, which takes effect the moment you first use the
                site. Massachusetts Institute of Technology (hereafter referred
                to as MIT) operates ODL Video and reserves the right at any time
                to change the terms, conditions and notices under which the
                services of ODL Video are offered, including but not limited to
                these Terms of Use, by posting such changes online. It is your
                responsibility to refer to and comply with these updated terms
                and conditions upon accessing the site. Your continued use of
                this site after changes are posted constitutes your acceptance
                of these terms and conditions as modified.
              </div>
              <div className="terms-div terms-underline">
                If these Terms of Use are not accepted in full, you do not have
                permission to access the contents of this site or to upload
                content to this site and you should cease using this site
                immediately.
              </div>
              <div className="terms-div">
                If there is any conflict between these Terms of Use and rules
                and/or specific terms of use appearing on this site relating to
                specific material, then the latter shall prevail.
              </div>

              <h3 className="terms-subheading">
                Availability and storage of video
              </h3>
              <div className="terms-div">
                ODL will host your streaming video for viewers for at least 2
                years. After that time, we may choose to take the video down. If
                and what happens we will contact you (via email) with
                instructions for how to request that it be restored.
              </div>
              <div className="terms-div">
                ODL will host your original source video files for at least 6
                years. At any time during those six years, you can download your
                source video (we will deliver it to you via MIT’s Dropbox).
                After that time, we may choose to remove the source files as
                well.
              </div>
              <h3 className="terms-subheading">
                Ability to accept Terms of Service
              </h3>
              <div className="terms-div">
                You affirm that you are either more than 17 years of age or
                possess legal parental or guardian consent, and are competent to
                enter into the terms, conditions, obligations, affirmations,
                representations and warranties set forth in these Terms of Use,
                and to abide by and comply with these Terms of Use.
              </div>
              <div className="terms-div">
                You must be 17 years or over or possess legal parental or
                guardian consent to register as a member of this website. If we
                discover or have any reason to suspect that you have not reached
                17 years of age or that you do not have legal parental or
                guardian consent, then we reserve the right to suspend or
                terminate your membership to this site immediately and without
                notice.
              </div>
              <div className="terms-div">
                Content uploaders agree not to upload any content that is not
                appropriate for an audience aged 12 years and up.
              </div>
              <h3 className="terms-subheading">Authentication</h3>
              <div className="terms-div">
                Users create accounts and log in to ODL Video through the MIT
                Touchstone Service. Users who do not have an MIT account can
                create a{" "}
                <a
                  href="https://idp.touchstonenetwork.net/cams/CreateAccount.action"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Touchstone Collaboration account
                </a>
                . Users are bound by the{" "}
                <a
                  href="https://idp.touchstonenetwork.net/cams/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Touchstone Rules of Use
                </a>
                .
              </div>
              <h3 className="terms-subheading">Privacy</h3>
              <div className="terms-div">
                Any private information and/or data relating to your user of ODL
                Video or your uploaded content that you are asked to supply or
                that you supply voluntarily as part of the registration process
                and as part of the upload/download process, will only be used by
                MIT ODL, our subcontractors, employees, agents, partners, and
                advisors, including legal advisors, as part of the process of
                administering your membership and when making decisions whether
                any material you seek to upload onto the site should be accepted
                or rejected. In addition, we may, at our discretion, disclose
                this information to the police, regulatory bodies or any legal
                advisers in connection with any alleged criminal offense or
                suspected breach of these Terms of Use, including but not
                limited to, any claim of infringement by you, or otherwise where
                required by law. Otherwise, this information will be kept
                private and confidential and will not be passed on to third
                parties without your express consent.
              </div>
              <h3 className="terms-subheading">
                Hold Harmless And Indemnification
              </h3>
              <div className="terms-div">
                You agree to hold harmless and indemnify MIT, its employees,
                agents and representatives, from and against any third party
                claim arising from or in any way related to your use of the ODL
                Video site, including any liability or expense arising from all
                claims, losses, damages (actual and consequential), suits,
                judgments, litigation costs and attorney's fees, of every kind
                and nature. If MIT receives notice of such a claim from someone
                other than the member whose use of the site is in question, MIT
                will provide that member with written notice of such claim, suit
                or action, at the email address provided by that member at the
                time of registration.
              </div>
              <h3 className="terms-subheading">Grant Of License</h3>
              <div className="terms-div">
                MIT does not claim ownership of the materials you post, upload,
                input or submit to the ODL Video site. However, by posting,
                uploading, inputting, providing or submitting your content to
                ODL Video, you are granting MIT, its affiliated organizations
                and partners, a worldwide, irrevocable, royalty-free,
                non-exclusive, sub-licensable license to use, reproduce, create
                derivative works of, distribute, publicly perform, publicly
                display, transfer, transmit, distribute and publish that content
                for the purposes of displaying that content on ODL Video or for
                any other educational or non-commercial use of that content.
              </div>
              <div className="terms-div">
                In addition, when you upload or post content to the ODL Video
                site, you grant MIT a license to distribute that content, either
                electronically or via other media, to users seeking to download
                it through the ODL Video site or for purposes of other services
                provided by ODL Video and to display such content on MIT
                affiliated sites. This license shall apply to the distribution
                and the storage of your content in any form, medium, or
                technology now known or later developed. By posting, uploading,
                inputting, providing or submitting your content, you warrant and
                represent that you own or otherwise control all of the rights to
                your content, including without limitation, all the rights
                necessary for you to provide, post, upload, input or submit the
                content and for ODL Video to post, upload, cross-post, or
                cross-upload the content.
              </div>
              <div className="terms-div">
                You may remove content you have posted on ODL Video at any time.
                When you delete content from ODL Video, such deleted content,
                while not available to the viewing public and other ODL Video
                users, will remain on the ODL Video server until such time as
                you make a specific request to ODL Video for permanent deletion
                of such content from the ODL Video server. Such requests must be
                made in writing, via email, to ODL Video customer service at the
                following address:{" "}
                <a href="mailto:odl-video-support@mit.edu">
                  odl-video-support@mit.edu
                </a>
                . When you do remove your content, the license described above
                will automatically expire.
              </div>
              <h3 className="terms-subheading">
                Copyright And Other Intellectual Property
              </h3>
              <div className="terms-div">
                The content on the ODL Video site, including without limitation,
                the text, software, graphics, photos, and videos, is owned by or
                licensed to MIT, subject to copyright and other intellectual
                property rights under United States Copyright Act and trademark
                laws, foreign laws, and international conventions. MIT reserves
                all rights not expressly granted in and to the website and said
                content. Other than as expressly permitted, you may not engage
                in the unauthorized use, copying, or distribution of any of said
                content.
              </div>
              <div className="terms-div">
                All copyright, trademarks, service marks and other intellectual
                property rights in this site (including the design, arrangement,
                and look and feel) and all material or content supplied as part
                of the site, other than user-generated content, shall remain at
                all times the property of MIT, its affiliates, associated
                organizations, and/or licensors.
              </div>
              <div className="terms-div">
                The names, images and logos identifying ODL Video are
                proprietary marks of MIT, its associated companies and/or
                affiliates. Nothing contained herein shall be construed as
                conferring by implication or otherwise any license or right
                under any trademark or service mark of MIT, its associated
                companies and affiliates, or any third party unless expressly
                stated otherwise.
              </div>
              <div className="terms-div">
                In accessing the ODL Video site, you agree that you do so only
                for your own personal, educational, or non-commercial use.
                Unless otherwise stated, you may not distribute, transmit,
                broadcast, commercially exploit or modify in any way the site's
                material or content or permit or assist any third party to do
                the same.
              </div>
              <div className="terms-div">
                You shall be solely responsible for your own user-generated
                content and the consequences of posting or publishing said
                content. In connection with all content that you upload to ODL
                Video, you affirm, represent and/or warrant to ODL Video and its
                third-party syndication, content and outreach partners that: (i)
                you own, or have the necessary licenses, rights, consents, and
                permissions to use, or are otherwise permitted by law to use
                (e.g. are using the content under Fair Use or the content is in
                the public domain), and authorize ODL Video to use, all patent,
                trademark, trade secret, copyright or other proprietary rights
                in and to said content; and (ii) you have the written consent,
                release, and/or permission of each and every identifiable
                individual person in any uploaded video to use the name or
                likeness of each and every such identifiable individual person
                in the manner contemplated by the website and these Terms of
                Use. In addition to posting your own content on ODL Video, you
                can also enjoy the many videos uploaded by others in the ODL
                Video community. The ODL Video site includes a combination of
                content that we license from third party partners and content
                that is created and posted by our users. All of the content on
                the ODL Video site is protected by our copyrights, the
                copyrights of our partners and/or the copyrights of the user who
                posted such materials. Materials uploaded to ODL Video may be
                subject to posted limitations on usage, reproduction and/or
                dissemination. You are responsible for adhering to such
                limitations if you download the materials.
              </div>
              <div className="terms-div">
                All user-generated content will be uploaded onto the site under
                a Creative Commons License (see{" "}
                <a
                  href="http://www.creativecommons.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  http://www.creativecommons.org/
                </a>
                ) or on an all rights reserved basis. You agree to be bound by
                the terms of each license. As a creator of user-generated
                content or as a passive user of the ODL Video site, you may not
                modify, publish, transmit, participate in the transfer or sale
                of, reproduce, create derivative works of, distribute, publicly
                perform, publicly display, or in any way exploit any of the
                content on the ODL Video site in whole or in part outside of the
                specific usage rights granted to you by each license. If you
                download or print a copy of any ODL Video content or
                user-generated content for personal use, you must retain all
                copyright and other proprietary notices contained therein. You
                may not otherwise use, reproduce, display, publicly perform, or
                distribute such content in any way for any public or commercial
                purpose unless such use is expressly granted by a particular
                license.
              </div>
              <div className="terms-div">
                If you believe that any of your intellectual property rights
                have been violated (e.g., your copyright or trademark infringed)
                by material available on ODL Video, please e-mail the following
                to{" "}
                <a href="mailto:odl-video-support@mit.edu">
                  odl-video-support@mit.edu
                </a>
                :
                <ul className="terms-list">
                  <li>
                    The nature of your complaint and an exact description of
                    where the material about which you complain is located
                    within the site;
                  </li>
                  <li>
                    In the case of a copyright/trademark dispute, identification
                    of the copyrighted/trademarked work that you claim has been
                    infringed and a statement by you that you have a good-faith
                    belief that the disputed use is not authorized by the
                    copyright/trademark owner, its agent, or the law;
                  </li>
                  <li>
                    Your name, address, telephone number, and email address;
                  </li>
                  <li>
                    A statement by you that the above information is accurate
                    and, in the case of a copyright/ trademark dispute, that you
                    are the owner of the copyright/trademark involved or are
                    authorized to act on behalf of that owner; and
                  </li>
                  <li>Your electronic or physical signature.</li>
                </ul>
              </div>
              <div className="terms-div">
                It is our policy to respond to notices of alleged infringement
                that comply with the Digital Millennium Copyright Act. For
                directions and more information on our copyright policy and
                procedure for reporting alleged copyright infringement, go to{" "}
                <a
                  href="http://web.mit.edu/stopit/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  http://web.mit.edu/stopit/
                </a>
                . Any rights not expressly granted herein are reserved.
              </div>
              <h3 className="terms-subheading">Prohibited Content</h3>
              <div className="terms-div">
                The following content is prohibited on ODL Video:
                <ul className="terms-list">
                  <li>
                    Content involving nudity, including but not limited to,
                    nudity or partial nudity of children of any age.
                  </li>
                  <li>
                    Content that exploits children or minors or that discloses
                    any personally identifying information beyond a first name
                    about persons under the age of 18.
                  </li>
                  <li>
                    Content that disseminates personal information about another
                    individual for malevolent purposes, including libel,
                    slander, defamation or harassment.
                  </li>
                  <li>
                    Content that is or may be deemed to be grossly offensive to
                    the online community, including but not limited to, blatant
                    expressions of bigotry, prejudice, racism, hatred and
                    profanity.
                  </li>
                  <li>
                    Content promoting or providing instructional information
                    about illegal activities.
                  </li>
                  <li>
                    Content promoting or providing instructional information
                    about dangerous activities.
                  </li>
                  <li>Content depicting cruelty to animals.</li>
                  <li>
                    Copyrighted content or material that is used without the
                    express permission of the owner.
                  </li>
                  <li>
                    Content intended to abuse, harass, stalk, threaten or
                    otherwise violate the legal rights of others (such as the
                    rights of privacy and publicity).
                  </li>
                  <li>
                    Content that contains software or other material protected
                    by intellectual property laws unless you own or control the
                    rights thereto or have secured all necessary consents and/or
                    licenses.
                  </li>
                  <li>
                    Content or other material that contains viruses, corrupted
                    files, or any other similar software or programs that may
                    damage the operation of ODL Video's server or another user's
                    computer.
                  </li>
                  <li>
                    Content that violates any applicable laws or regulations not
                    specifically referenced herein.
                  </li>
                </ul>
              </div>
              <div className="terms-div">
                As a condition of your use of the ODL Video site, you warrant
                that you will not use the services offered on the site for any
                purpose that is unlawful or prohibited by these terms,
                conditions, and notices. You may not use the ODL Video site in
                any manner which could damage, disable, overburden, or impair
                the ODL Video site or interfere with any other party’s use and
                enjoyment of the ODL Video site. You may not obtain or attempt
                to obtain any materials or information, including but not
                limited to, software and other ODL Video proprietary materials,
                through any means not intentionally made available or provided
                for through the ODL Video site. ODL Video reserves the right to
                review materials uploaded to ODL Video and to remove any
                materials in its sole discretion for any reason or no reason, at
                any time, with or without notice to you. ODL Video reserves the
                right to terminate your access to any or all of the services
                offered by ODL Video at any time without notice for any reason
                whatsoever.
              </div>
              <div className="terms-div">
                ODL Video does not endorse or entirely control the content,
                messages or information found in any user-generated content or
                uploaded material and, therefore, ODL Video specifically
                disclaims any liability with regard to such user-generated
                content or uploaded material and any actions resulting from such
                user-generated content or uploaded material. You agree to use
                the services provided by ODL Video only for their intended,
                lawful purposes and in accordance with all applicable laws. You
                agree not to use ODL Video in any manner that interferes with
                its normal operation or with any other user’s use and enjoyment
                thereof. You further agree that you will not access ODL Video by
                any means except through the interface provided by ODL Video and
                that you will not access ODL Video from any territory where its
                contents are illegal.
              </div>
              <div className="terms-div">
                ODL Video does not endorse any user-generated content or any
                opinion, recommendation or advice expressed therein, and ODL
                Video expressly disclaims any and all liability in connection
                with user-generated content. If notified by a user or a third
                party of uploaded material that allegedly does not conform to
                these Terms of Use, MIT may investigate the allegation and
                determine in good faith and in its sole discretion whether to
                remove the user-generated content.
              </div>

              <h3 classNam="terms-subheading">Warranty Disclaimer</h3>
              <div className="terms-div">
                Please note that the information, software, products and
                services included in, or available through, the ODL Video
                website are continually being updated and upgraded. MIT does not
                represent that they are reliable, accurate, complete, or
                otherwise valid. ACCORDINGLY, THE SITE IS PROVIDED AS IS WITH NO
                WARRANTY OF ANY KIND AND YOU USE THE SERVICE AT YOUR OWN RISK.
                MIT EXPRESSLY DISCLAIMS ANY WARRANTY, EXPRESS OR IMPLIED,
                REGARDING THE ODL VIDEO SITE OR ITS CONTENT, INCLUDING BUT NOT
                LIMITED TO, ANY IMPLIED WARRANTY OF MERCHANTABILITY, WARRANTY OF
                SATISFACTORY PURPOSE, FITNESS FOR A PARTICULAR PURPOSE,
                NON-INFRINGEMENT, COMPATIBILITY, SECURITY AND ACCURACY. Some
                states do not allow the exclusion of warranty, so the above
                exclusions may not apply to you.
              </div>
              <div className="terms-div">
                The information and other materials included on this site may
                contain inaccuracies and typographical errors. MIT does not
                warrant the accuracy or completeness of the information and
                materials or the reliability of any statement or other
                information displayed or distributed through the site
                (including, without limitation, the information provided through
                the use of any software or any user-generated content). You
                acknowledge that any reliance on any such statement or
                information shall be at your sole risk. MIT reserves the right,
                in its sole discretion, to correct any errors or omissions in
                any part of the site and to make changes to the site and to the
                materials, products, programs, services or prices described in
                the site at any time without notice. MIT does not warrant that
                the functions contained in this site will be uninterrupted or
                error free, that defects will be corrected or that this site or
                the server that makes it available are free of viruses or bugs.
                MIT does not represent the full functionality, accuracy or
                reliability of any material. MIT may terminate, change, suspend
                or discontinue any aspect of this site, including the
                availability of any features of the site, at any time without
                notice or liability.
              </div>
              <h3>Limitation of Liability</h3>
              <div className="terms-div">
                TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT
                SHALL MIT AND/OR ITS EMPLOYEES, AGENTS OR AFFILIATES, BE LIABLE
                FOR ANY DIRECT, INDIRECT, PUNITIVE, INCIDENTAL, SPECIAL OR
                CONSEQUENTIAL DAMAGES, OR ANY DAMAGES WHATSOEVER, INCLUDING
                WITHOUT LIMITATION, DAMAGES FOR LOSS OF USE, DATA OR PROFITS,
                ARISING OUT OF OR IN ANY WAY CONNECTED WITH THE USE OR
                PERFORMANCE OF THE ODL VIDEO WEBSITE, WITH THE DELAY OR
                INABILITY TO USE THE ODL VIDEO WEBSITE OR RELATED SERVICES, THE
                PROVISION OF OR FAILURE TO PROVIDE SERVICES, OR FOR ANY
                INFORMATION, SOFTWARE, PRODUCTS, SERVICES AND RELATED GRAPHICS
                OBTAINED THROUGH THE ODL VIDEO WEBSITE, OR OTHERWISE ARISING OUT
                OF THE USE OF THE ODL VIDEO WEBSITE, WHETHER BASED ON CONTRACT,
                TORT, NEGLIGENCE, STRICT LIABILITY OR OTHERWISE, EVEN IF ODL
                VIDEO OR ANY OF ITS AFFILIATES HAS BEEN ADVISED OF THE
                POSSIBILITY OF DAMAGES. Because some states/jurisdictions do not
                allow the exclusion or limitation of liability for consequential
                or incidental damages, the above limitation may not apply to
                you. If you are dissatisfied with any portion of the ODL Video
                website, or with any of these Terms of Use, your sole and
                exclusive remedy is to discontinue using the ODL Video website
                and services provided therein.
              </div>
              <h3 className="terms-subheading">LAW AND JURISDICTION</h3>
              <div className="terms-div">
                These Terms of Use shall be governed by and construed in
                accordance with the laws of the State of Massachusetts. Disputes
                arising from these Terms of Use or your use of the ODL Video
                website shall be exclusively subject to the jurisdiction of the
                courts of Massachusetts. Any cause of action you may have with
                respect to your use of this site must be commenced within one
                (1) year after the claim or cause of action arises. MIT makes no
                representation that materials on this site are appropriate or
                available for use at other locations outside of the United
                States and access to them from territories where their contents
                are illegal is strictly prohibited. If you access this site from
                a location outside of the United States, you are responsible for
                compliance with all local laws.
              </div>
              <h3 className="terms-subheading">Miscellaneous</h3>
              <div className="terms-div">
                If any of these Terms of Use or any other policies posted by MIT
                on the ODL Video website should be determined to be illegal,
                invalid or otherwise unenforceable by reason of the law of any
                state or country in which these Terms of Use are intended to be
                effective, then to the extent permissible, such Term of Use or
                policy, or portion thereof, shall be severed and deleted from
                the remaining terms, conditions and policies, and the remaining
                terms, conditions and policies shall survive and continue to be
                binding and enforceable. The failure of MIT to exercise or
                enforce any right or provision of these terms and conditions
                shall not constitute a waiver of such right or provision.
              </div>
              <div className="terms-div">
                The section headings contained in these Terms of Use are
                included for convenience only, and shall not limit or otherwise
                affect these terms and conditions.
              </div>
            </div>
          </div>
        </div>
      </WithDrawer>
    )
  }
}

export default connect()(TermsPage)
